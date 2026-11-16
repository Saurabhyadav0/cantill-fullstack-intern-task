"""Policy amendments: apply structured ops to a policy document, summarise them in
plain language, and parse a natural-language / document description into ops.

An amendment never changes code: it produces a NEW policy document (new version), which
the engine then interprets. Supports changing params, changing thresholds, and ADDING a
new kind of rule (e.g. plant-specific) — the core of the blind-test Run 2.
"""
from __future__ import annotations

import copy
import json
import os
import re

OPS_HELP = {
    "set_param": "set a value at a dotted path, e.g. parameters.clubbing.create_window_days",
    "set_rule_value": "change a threshold on a rule, e.g. rule 5.4 value -> 300000",
    "add_rule": "insert a new rule (optionally before another rule id)",
    "remove_rule": "remove a rule by id",
    "set_meta": "set version / effective_date",
}


# --------------------------------------------------------------------------- #
# Path resolution: supports keys, list indices, and rules[id=5.4] selectors.
# --------------------------------------------------------------------------- #
def _walk(obj, path, create=False):
    parts = re.findall(r"[^.\[\]]+|\[[^\]]+\]", path)
    cur = obj
    for i, raw in enumerate(parts):
        last = i == len(parts) - 1
        if raw.startswith("["):
            sel = raw[1:-1]
            if "=" in sel:                      # rules[id=5.4]
                k, v = sel.split("=", 1)
                idx = next((j for j, e in enumerate(cur) if str(e.get(k)) == v), None)
                if idx is None:
                    raise KeyError(f"no element with {k}={v}")
            else:
                idx = int(sel)
            if last:
                return cur, idx
            cur = cur[idx]
        else:
            if last:
                return cur, raw
            if raw not in cur and create:
                cur[raw] = {}
            cur = cur[raw]
    return cur, None


def _set_path(doc, path, value):
    container, key = _walk(doc, path, create=True)
    container[key] = value


def _get_path(doc, path):
    try:
        container, key = _walk(doc, path)
        return container[key]
    except (KeyError, IndexError, TypeError):
        return None


# --------------------------------------------------------------------------- #
def apply_ops(doc: dict, ops: list) -> dict:
    new = copy.deepcopy(doc)
    for op in ops:
        kind = op["op"]
        if kind == "set_param":
            _set_path(new, op["path"], op["value"])
        elif kind == "set_rule_value":
            # convenience: change the .value of a rule's single condition
            rid = op["rule_id"]
            rule = next((r for r in new["rules"] if str(r.get("id")) == str(rid)), None)
            if rule is None:
                raise KeyError(f"rule {rid} not found")
            conds = rule["when"].get("all") or rule["when"].get("any") or [rule["when"]]
            field = op.get("field")
            target = None
            for c in conds:
                if field is None or c.get("field") == field:
                    target = c
                    break
            if target is None:
                raise KeyError(f"no condition to change on rule {rid}")
            target["value"] = op["value"]
        elif kind == "add_rule":
            rule = op["rule"]
            before = op.get("before")
            if before:
                idx = next((j for j, r in enumerate(new["rules"]) if str(r.get("id")) == str(before)), len(new["rules"]))
                new["rules"].insert(idx, rule)
            else:
                new["rules"].append(rule)
        elif kind == "remove_rule":
            new["rules"] = [r for r in new["rules"] if str(r.get("id")) != str(op["rule_id"])]
        elif kind == "set_meta":
            for k, v in op.get("values", {}).items():
                new[k] = v
        else:
            raise ValueError(f"unknown op: {kind}")
    return new


# --------------------------------------------------------------------------- #
_RULE_NAMES = {"5.1": "Capex", "5.2": "Contract PO", "5.3": "Emergency PO",
               "5.4": "Spot PO", "5.5": "RFQ", "5.6": "RFP"}


def summarise(old: dict, ops: list) -> list:
    """Plain-language description of each op's effect."""
    out = []
    for op in ops:
        k = op["op"]
        if k == "set_param":
            was = _get_path(old, op["path"])
            out.append(f"Set `{op['path']}` from **{was}** to **{op['value']}**.")
        elif k == "set_rule_value":
            name = _RULE_NAMES.get(str(op["rule_id"]), f"rule {op['rule_id']}")
            rule = next((r for r in old.get("rules", []) if str(r.get("id")) == str(op["rule_id"])), None)
            was = None
            if rule:
                conds = rule["when"].get("all") or rule["when"].get("any") or [rule["when"]]
                was = conds[0].get("value") if conds else None
            out.append(f"Change **{name}** threshold from **{_inr(was)}** to **{_inr(op['value'])}**.")
        elif k == "add_rule":
            r = op["rule"]
            where = f" before rule {op['before']}" if op.get("before") else ""
            out.append(f"**Add a new rule** `{r.get('id')}` ({r.get('name','')}) -> "
                       f"{r.get('outcome',{}).get('route','?')}{where}. "
                       f"Condition: {_conds_text(r.get('when',{}))}.")
        elif k == "remove_rule":
            out.append(f"**Remove rule** {op['rule_id']}.")
        elif k == "set_meta":
            out.append("Set " + ", ".join(f"{a}=**{b}**" for a, b in op.get("values", {}).items()) + ".")
    return out


def _inr(v):
    try:
        return f"Rs {int(v):,}"
    except (TypeError, ValueError):
        return str(v)


def _conds_text(when):
    conds = when.get("all") or when.get("any") or ([when] if when else [])
    bits = []
    for c in conds:
        if "field" in c:
            bits.append(f"{c['field']} {c.get('op')} {c.get('value')}")
    return " AND ".join(bits) if bits else "always"


# --------------------------------------------------------------------------- #
# Natural-language -> ops.  Heuristics cover the common cases; if ANTHROPIC_API_KEY
# is set, an LLM handles arbitrary amendment text/documents.
# --------------------------------------------------------------------------- #
_NUM = r"(?:rs\.?\s*)?([\d,]+(?:\.\d+)?)"


def _to_num(s):
    s = s.replace(",", "")
    # handle "2 lakh" / "3L"
    return float(s)


def parse_nl(text: str, doc: dict) -> list:
    """Best-effort heuristic parse. Returns a list of ops (possibly empty)."""
    t = text.lower().replace("₹", "rs ")
    t = re.sub(r"(\d)\s*lakh", lambda m: str(int(m.group(1)) * 100000), t)
    t = re.sub(r"(\d)\s*l\b", lambda m: str(int(m.group(1)) * 100000), t)
    ops = []

    # Spot PO limit
    m = re.search(r"spot[^\d]*(?:limit|threshold|below|to)[^\d]*" + _NUM, t)
    if m:
        ops.append({"op": "set_rule_value", "rule_id": "5.4", "value": _to_num(m.group(1))})
    # RFP / large threshold
    m = re.search(r"(?:rfp|formal)[^\d]*(?:limit|threshold|above|at or above|to)[^\d]*" + _NUM, t)
    if m:
        ops.append({"op": "set_rule_value", "rule_id": "5.6", "value": _to_num(m.group(1))})
    # Emergency cap
    m = re.search(r"emergency[^\d]*(?:cap|limit|threshold|up to|to)[^\d]*" + _NUM, t)
    if m:
        ops.append({"op": "set_rule_value", "rule_id": "5.3", "value": _to_num(m.group(1))})
    # clubbing create window
    m = re.search(r"(?:club|clubbing|create)[^\d]*(\d+)\s*(?:calendar\s*)?days", t)
    if m:
        ops.append({"op": "set_param", "path": "parameters.clubbing.create_window_days", "value": int(m.group(1))})
    # need-by window
    m = re.search(r"need[- ]?by[^\d]*(\d+)\s*days", t)
    if m:
        ops.append({"op": "set_param", "path": "parameters.clubbing.need_by_window_days", "value": int(m.group(1))})
    return ops


def parse_with_llm(text: str, doc: dict):
    """Optional: use Claude to turn an amendment document/description into ops.
    Returns (ops, used_llm: bool). Falls back to heuristics if unavailable.
    """
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return parse_nl(text, doc), False
    try:
        import anthropic
    except Exception:
        return parse_nl(text, doc), False
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    sys_prompt = (
        "You convert a procurement policy amendment into a JSON list of ops for this schema. "
        "Ops: set_param{path,value}; set_rule_value{rule_id,value,field?}; "
        "add_rule{rule{id,clause,name,when{all:[{field,op,value}]},outcome{decision,route,supplier_strategy,price?}},before?}; "
        "remove_rule{rule_id}; set_meta{values}. "
        "Rule ids: 5.1 Capex, 5.2 Contract, 5.3 Emergency(<=value), 5.4 SpotPO(<value), 5.5 RFQ(<value), 5.6 RFP(>=value). "
        "Fields available: item.item_type, requirement.plant, requirement.value, requirement.is_emergency, "
        "requirement.usable_contract, requirement.bought_from_active_supplier_within_365d, requirement.category. "
        "Routes: CONTRACT_PO, EMERGENCY_PO, SPOT_PO, RFQ, RFP, CAPEX_SOURCING. "
        "supplier_strategy in {contract_supplier, first_preferred, suggest_3, suggest_5}. "
        "Return ONLY a JSON object: {\"ops\":[...], \"effective_date\":\"YYYY-MM-DD\"|null, \"version\":\"x\"|null}."
    )
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=model, max_tokens=1500, system=sys_prompt,
            messages=[{"role": "user", "content": f"Current policy:\n{json.dumps(doc)[:6000]}\n\nAmendment:\n{text}"}],
        )
        raw = msg.content[0].text
        raw = re.search(r"\{.*\}", raw, re.S).group(0)
        parsed = json.loads(raw)
        ops = parsed.get("ops", [])
        if parsed.get("effective_date") or parsed.get("version"):
            vals = {}
            if parsed.get("effective_date"):
                vals["effective_date"] = parsed["effective_date"]
            if parsed.get("version"):
                vals["version"] = parsed["version"]
            ops.append({"op": "set_meta", "values": vals})
        return ops, True
    except Exception:
        return parse_nl(text, doc), False
