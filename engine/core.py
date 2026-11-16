"""The decision engine pipeline (policy sections 1-8).

match items -> club into requirements -> value + choose contract -> apply ordered
decision rules -> build preferred lists / suggestions -> consolidate POs -> emit rows.

Everything that is a policy knob (windows, thresholds, rule order, outcomes) is read
from the Policy document, not hard-coded here.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .matching import NEW, match_item
from .models import DecisionRow, PRLine, Requirement
from .policy import Policy


class MasterData:
    def __init__(self, items, suppliers, po_history, contracts, plants=None):
        self.items = list(items)
        self.items_by_code = {i.item_code: i for i in self.items}
        self.suppliers = list(suppliers)
        self.suppliers_by_id = {s.supplier_id: s for s in self.suppliers}
        self.po_history = list(po_history)
        self.contracts = list(contracts)
        self.plants = plants or []


def _round_rupee(x: Optional[float]):
    if x is None:
        return None
    return int(round(x))


# --------------------------------------------------------------------------- #
# Preferred supplier list (policy section 6)
# --------------------------------------------------------------------------- #
class PreferredEngine:
    def __init__(self, md: MasterData, policy: Policy):
        self.md = md
        self.p = policy
        pref = policy.preferred
        self.elig_days = pref.get("eligibility_lookback_days", 548)
        self.ref_days = pref.get("reference_price_lookback_days", 548)
        self.weights = pref.get("ranking_weights", {})
        self.buckets = self.weights.get("recency_buckets", {"within_90d": 1.0, "within_365d": 0.5, "older": 0.0})
        self.guard = set(policy.guard_statuses())

    def _pos_for(self, item_code, supplier_id, as_of: date, days: int):
        lo = as_of - timedelta(days=days)
        return [po for po in self.md.po_history
                if po.item_code == item_code and po.supplier_id == supplier_id
                and lo <= po.po_date <= as_of]

    def _contracts_for(self, item_code, supplier_id, as_of: date):
        return [c for c in self.md.contracts
                if c.supplier_id == supplier_id and c.covers(item_code)
                and c.start_date <= as_of]

    def reference_price(self, item_code, supplier_id, as_of: date):
        pos = sorted(self._pos_for(item_code, supplier_id, as_of, self.ref_days),
                     key=lambda po: (po.po_date, po.po_number), reverse=True)
        if pos:
            return pos[0].unit_price
        cons = sorted(self._contracts_for(item_code, supplier_id, as_of),
                      key=lambda c: c.start_date, reverse=True)
        if cons:
            return cons[0].rate_for(item_code)
        return None

    def _recency(self, item_code, supplier_id, as_of: date):
        pos = self._pos_for(item_code, supplier_id, as_of, self.elig_days)
        if not pos:
            return 0.0
        latest = max(po.po_date for po in pos)
        age = (as_of - latest).days
        if age <= 90:
            return self.buckets.get("within_90d", 1.0)
        if age <= 365:
            return self.buckets.get("within_365d", 0.5)
        return self.buckets.get("older", 0.0)

    def ranked_list(self, item_code, as_of: date):
        """Return [(supplier, score, reference_price)] ranked best-first (policy 6.1-6.3)."""
        candidates = []
        counts = {}
        for s in self.md.suppliers:
            if s.status in self.guard:          # Active-only list (6.1 + 5.7)
                continue
            pos = self._pos_for(item_code, s.supplier_id, as_of, self.elig_days)
            has_contract = bool(self._contracts_for(item_code, s.supplier_id, as_of))
            if not pos and not has_contract:
                continue
            counts[s.supplier_id] = len(pos)
            candidates.append((s, len(pos), has_contract))

        if not candidates:
            return []
        max_count = max((c for _, c, _ in candidates), default=0) or 1

        w = self.weights
        scored = []
        for s, cnt, has_contract in candidates:
            recency = self._recency(item_code, s.supplier_id, as_of)
            score = (
                w.get("po_frequency_548d", 0.30) * (cnt / max_count)
                + w.get("recency", 0.25) * recency
                + w.get("held_contract", 0.20) * (1.0 if has_contract else 0.0)
                + w.get("on_time_pct", 0.15) * (s.on_time_pct / 100.0)
                + w.get("quality_rating", 0.10) * (s.quality_rating / 5.0)
            )
            ref = self.reference_price(item_code, s.supplier_id, as_of)
            scored.append((s, score, ref, cnt, recency))
        # tie-break: score, then po count, then on-time, then supplier_id
        scored.sort(key=lambda x: (-x[1], -x[3], -x[0].on_time_pct, x[0].supplier_id))
        return [(s, score, ref) for (s, score, ref, _, _) in scored]

    def suggestions(self, item_code, category, as_of: date, n: int):
        """Preferred list topped up from the item's category (policy 6.4)."""
        ranked = self.ranked_list(item_code, as_of)
        ids = [s.supplier_id for s, _, _ in ranked]
        if len(ids) < n:
            extra = [s for s in self.md.suppliers
                     if s.status not in self.guard
                     and category and category in (s.categories or ())
                     and s.supplier_id not in ids]
            # policy 6.4: "best delivery and quality record first" -> combined score
            extra.sort(key=lambda s: (-(s.on_time_pct / 100.0 + s.quality_rating / 5.0), s.supplier_id))
            for s in extra:
                if len(ids) >= n:
                    break
                ids.append(s.supplier_id)
        return ids[:n]


# --------------------------------------------------------------------------- #
# Contracts + valuation (policy sections 3, 4)
# --------------------------------------------------------------------------- #
class ContractEngine:
    def __init__(self, md: MasterData, policy: Policy):
        self.md = md
        self.p = policy
        self._consumed = {c.contract_id: c.consumed_value for c in md.contracts}

    def applicable(self, item_code, as_of: date):
        out = []
        for c in self.md.contracts:
            if not c.covers(item_code):
                continue
            if not (c.start_date <= as_of <= c.end_date):     # inclusive (4.1)
                continue
            sup = self.md.suppliers_by_id.get(c.supplier_id)
            if not sup or not sup.is_active:                  # supplier Active (4.1)
                continue
            out.append(c)
        return out

    def choose(self, item_code, total_qty, as_of: date):
        """Return (usable_contract_or_None, priced_rate_or_None, applicable_list).

        Picks the lowest-rate applicable contract that still has ceiling at this
        requirement's value (4.3). Does NOT consume yet.
        """
        applicable = self.applicable(item_code, as_of)
        if not applicable:
            return None, None, []
        by_rate = sorted(applicable, key=lambda c: c.rate_for(item_code))
        usable = None
        for c in by_rate:
            rate = c.rate_for(item_code)
            value = total_qty * rate
            if self._consumed[c.contract_id] + value <= c.value_cap + 1e-6:   # ceiling left (4.2)
                usable = c
                break
        # valuation rate (3.1a): chosen contract's rate, else lowest applicable rate
        priced_rate = (usable.rate_for(item_code) if usable
                       else by_rate[0].rate_for(item_code))
        return usable, priced_rate, applicable

    def consume(self, contract: "Contract", value: float):
        self._consumed[contract.contract_id] += value

    def consumed(self, contract_id: str):
        return self._consumed[contract_id]


# --------------------------------------------------------------------------- #
# The engine
# --------------------------------------------------------------------------- #
class DecisionEngine:
    def __init__(self, md: MasterData, policy: Policy):
        self.md = md
        self.p = policy
        self.pref = PreferredEngine(md, policy)
        self.guard = set(policy.guard_statuses())

    # ---- helpers ---------------------------------------------------------- #
    def _recent_po_price(self, item_code, as_of: date):
        lo = as_of - timedelta(days=self.p.valuation.get("recent_po_lookback_days", 365))
        pos = [po for po in self.md.po_history
               if po.item_code == item_code and lo <= po.po_date <= as_of]
        if not pos:
            return None
        return max(pos, key=lambda po: (po.po_date, po.po_number)).unit_price

    def _bought_from_active_within(self, item_code, as_of: date, days=365):
        lo = as_of - timedelta(days=days)
        for po in self.md.po_history:
            if po.item_code != item_code or not (lo <= po.po_date <= as_of):
                continue
            sup = self.md.suppliers_by_id.get(po.supplier_id)
            if sup and sup.is_active:
                return True
        return False

    # ---- clubbing (section 2) -------------------------------------------- #
    def _club(self, lines: list) -> list:
        club = self.p.clubbing
        create_window = club.get("create_window_days", 14)
        needby_window = club.get("need_by_window_days", 7)

        order = sorted(lines, key=lambda l: (l.created_at, l.pr_no, l.pr_line))
        reqs: list[Requirement] = []
        seq = 0
        for ln in order:
            if ln.resolved_item_code == NEW:
                seq += 1
                reqs.append(Requirement(group_id=f"REQ-{seq:04d}", lines=[ln],
                                        resolved_item_code=NEW, plant=ln.plant, is_new_item=True))
                continue
            # candidate existing requirements, earliest first (2.2 "joins the earliest")
            joined = None
            for r in reqs:
                if r.is_new_item or r.resolved_item_code != ln.resolved_item_code or r.plant != ln.plant:
                    continue
                first = r.first_line
                dcreate = (ln.created_at.date() - first.created_at.date()).days
                if not (0 <= dcreate <= create_window):
                    continue
                if ln.need_by_date and first.need_by_date:
                    if abs((ln.need_by_date - first.need_by_date).days) > needby_window:
                        continue
                joined = r
                break
            if joined:
                joined.lines.append(ln)
            else:
                seq += 1
                reqs.append(Requirement(group_id=f"REQ-{seq:04d}", lines=[ln],
                                        resolved_item_code=ln.resolved_item_code, plant=ln.plant))
        return reqs

    # ---- value one requirement + decide its route ------------------------ #
    def _value_and_decide(self, r: Requirement, contracts: "ContractEngine"):
        item = self.md.items_by_code.get(r.resolved_item_code)
        as_of = r.requirement_date

        # ---- NEW item (1.2): always sourcing, valued at estimate, never clubbed ----
        if r.is_new_item:
            est = r.first_line.estimated_unit_price or 0.0
            r.unit_price = est
            r.value = r.total_quantity * est
            r.value_basis = "requester estimate (1.2)"
            r.decision, r.route = "SOURCING_REQUEST", "NEW_ITEM_SOURCING"
            r.clause = "1.2"
            r.reason = f"No item master match ({r.first_line.match_note}); new item to sourcing (1.2)."
            r.suggested_supplier_ids = []
            return

        # ---- valuation (3.1) + contract choice (4) ----
        usable, priced_rate, applicable = contracts.choose(
            r.resolved_item_code, r.total_quantity, as_of)
        if priced_rate is not None:
            r.unit_price, r.value_basis = priced_rate, (
                "contract rate (3.1a)" if usable else "lowest applicable contract rate (3.1a)")
        else:
            recent = self._recent_po_price(r.resolved_item_code, as_of)
            if recent is not None:
                r.unit_price, r.value_basis = recent, "most recent PO within 365d (3.1b)"
            else:
                r.unit_price = item.standard_price if item else 0.0
                r.value_basis = "item master standard price (3.1c)"
        r.value = r.total_quantity * r.unit_price
        r.usable_contract = usable
        r.priced_contract_rate = priced_rate

        # ---- build decision context for the policy interpreter ----
        bought = self._bought_from_active_within(r.resolved_item_code, as_of, 365)
        context = {
            "item": {"item_type": item.item_type if item else None,
                     "category": item.category if item else None},
            "requirement": {
                "plant": r.plant,
                "value": r.value,
                "is_emergency": r.is_emergency,
                "urgency": "Emergency" if r.is_emergency else "Normal",
                "usable_contract": r.usable_contract is not None,
                "bought_from_active_supplier_within_365d": bought,
                "category": item.category if item else None,
            },
        }
        rule = self.p.first_matching_rule(context)
        if rule is None:
            r.decision, r.route, r.clause = "SOURCING_REQUEST", "RFQ", "fallback"
            r.reason = "No policy rule matched; defaulted to RFQ. Review."
            r.suggested_supplier_ids = self.pref.suggestions(
                r.resolved_item_code, context["item"]["category"], as_of, 3)
            return

        out = rule["outcome"]
        r.decision, r.route, r.clause = out["decision"], out["route"], rule.get("clause", rule.get("id"))
        self._apply_outcome(r, out, usable, as_of, context["item"]["category"])

    def _apply_outcome(self, r, out, usable, as_of, category):
        strat = out.get("supplier_strategy")
        if out.get("route") == "CONTRACT_PO" and usable is not None:
            r.supplier_id = usable.supplier_id
            r.po_unit_price = usable.rate_for(r.resolved_item_code)
            # consume ceiling now that we've committed (4.2)
            # (ContractEngine instance is shared; consume via closure not available here,
            #  so consumption is handled in process() right after.)
            r.reason = (f"Contract {usable.contract_id} ({usable.supplier_name}) covers the item, "
                        f"valid on {as_of}, supplier Active, ceiling left (5.2/4.1-4.3).")
            self._pending_consume = (usable, r.value)
        elif strat == "first_preferred":
            ranked = self.pref.ranked_list(r.resolved_item_code, as_of)
            if ranked:
                s, _, ref = ranked[0]
                r.supplier_id = s.supplier_id
                r.po_unit_price = ref
            r.reason = (f"{r.route} to 1st preferred supplier at reference price "
                        f"(clause {r.clause}); value Rs {int(round(r.value))}.")
        elif strat in ("suggest_3", "suggest_5"):
            n = 3 if strat == "suggest_3" else 5
            r.suggested_supplier_ids = self.pref.suggestions(r.resolved_item_code, category, as_of, n)
            r.reason = (f"{r.route}: value Rs {int(round(r.value))} (clause {r.clause}); "
                        f"{len(r.suggested_supplier_ids)} suppliers suggested (6.4).")
        else:
            r.reason = f"{r.route} (clause {r.clause})."

    # process() drives consumption to keep ContractEngine authoritative
    def _emit(self, lines, reqs):
        by_group = {}
        for r in reqs:
            for l in r.lines:
                by_group[(l.pr_no, l.pr_line)] = r
        rows = []
        for l in lines:
            r = by_group[(l.pr_no, l.pr_line)]
            sugg = ";".join(r.suggested_supplier_ids) if r.suggested_supplier_ids else ""
            rows.append(DecisionRow(
                pr_no=l.pr_no, pr_line=l.pr_line,
                resolved_item_code=r.resolved_item_code,
                group_id=r.group_id,
                po_id=r.po_id or "",
                decision=r.decision, route=r.route,
                supplier_id=r.supplier_id or "",
                unit_price=("" if r.po_unit_price is None else str(_round_rupee(r.po_unit_price))),
                group_value_inr=("" if r.is_new_item and not r.first_line.estimated_unit_price
                                 else str(_round_rupee(r.value))),
                suggested_supplier_ids=sugg,
                policy_version=r.policy_version,
                reason=r.reason,
            ))
        return rows

    # ---- consolidation (section 7) --------------------------------------- #
    def _consolidate(self, reqs):
        window_h = self.p.consolidation.get("combine_window_hours", 24)
        po_reqs = [r for r in reqs if r.decision == "PO"]
        po_reqs.sort(key=lambda r: (r.first_line.created_at, r.first_line.pr_no, r.first_line.pr_line))
        open_pos = []   # list of dicts: {po_id, anchor, supplier, plant, route}
        seq = 0
        for r in po_reqs:
            key = (r.supplier_id, r.plant, r.route)
            joined = None
            for po in open_pos:
                if po["key"] != key:
                    continue
                if (r.first_line.created_at - po["anchor"]) <= timedelta(hours=window_h):
                    joined = po
                    break
            if joined:
                r.po_id = joined["po_id"]
            else:
                seq += 1
                pid = f"PO-{seq:04d}"
                open_pos.append({"po_id": pid, "key": key, "anchor": r.first_line.created_at})
                r.po_id = pid


def process_batch(md: MasterData, policy: Policy, lines: list):
    """Public entry point. Returns (rows: list[DecisionRow], requirements: list[Requirement])."""
    eng = DecisionEngine(md, policy)
    for ln in lines:
        code, conf, note = match_item(ln.item_code, ln.description,
                                      eng.md.items_by_code, eng.md.items)
        ln.resolved_item_code, ln.match_confidence, ln.match_note = code, conf, note
    reqs = eng._club(lines)
    for r in reqs:
        r.requirement_date = min(l.created_at for l in r.lines).date()
        r.is_emergency = any((l.urgency or "").lower() == "emergency" for l in r.lines)
        r.total_quantity = sum(l.quantity for l in r.lines)
        r.policy_version = eng.p.version
    contracts = ContractEngine(eng.md, eng.p)
    order = sorted(reqs, key=lambda r: (r.requirement_date, r.first_line.created_at,
                                        r.first_line.pr_no, r.first_line.pr_line))
    for r in order:
        eng._pending_consume = None
        eng._value_and_decide(r, contracts)
        if getattr(eng, "_pending_consume", None):
            c, v = eng._pending_consume
            contracts.consume(c, v)
    eng._consolidate(reqs)
    return eng._emit(lines, reqs), reqs
