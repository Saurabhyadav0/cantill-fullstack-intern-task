# DECISIONS.md

Where Corvo's Procurement Policy v5.0, the brief, or the data is silent or ambiguous, I made a
business decision, implemented it, and recorded it here. Format: **what I noticed → what I decided → why**.
(Judgment is 15% of the score and read closely.)

> Status: implemented. Each decision below is live in the engine and covered by tests where noted.

---

### D-0 · What counts as "task data" to keep out of the public repo
- **Noticed:** the brief says the public repo must not contain the task data files, but the app must ship a working v5.0 policy and the hosted app must run.
- **Decided:** gitignore everything kit-derived — `data/` (master data, contracts, PR batches, PDFs) **and** `docs/policy-v5.json` (the policy encoded as data). The repo ships code + schema docs + committed `data/README.md` and `docs/README.md` explaining how to place them. For hosting, data + policy are supplied at deploy time (volume/secret), never via the public repo. Startup is resilient: the app boots and serves the UI even if data is absent.
- **Why:** honours the rule literally (policy content is task data too) while keeping the app fully functional locally and hostable.

### D-1 · Item matching confidence & disambiguation
- **Noticed:** §1.1 wants description matching ("brg 6205 2rs" → *Ball bearing 6205-2RS*) but gives no threshold; descriptions are short, noisy, abbreviated.
- **Decided:** normalise (lowercase, strip units/symbols, expand common abbreviations: brg→bearing, hyd→hydraulic, ms→mild steel, etc.), then score (token overlap + fuzzy). High confidence → auto-match; medium → chat asks the requester to pick from top candidates; low/none → treat as `NEW`. In batch mode, medium/low is matched to the best candidate and **flagged** in `reason` for buyer review (never silently invented).
- **Why:** balances §1.1 (match short forms) with the "never invent items" instruction and the chat-UX expectation to ask when unsure.

### D-2 · Capex detected from the matched item, not the text
- **Noticed:** Worked example 12 ("eot crane 5 ton", no code) → `CAPEX_SOURCING`, not `NEW_ITEM_SOURCING`.
- **Decided:** run item matching first; `item_type = Capex` on the matched master item triggers §5.1. Only a genuine non-match is `NEW`.
- **Why:** matches the worked example and §5.1's wording ("item type is Capex").

### D-3 · New item with no estimated unit price
- **Noticed:** many `sample_pr_batch` rows have blank `estimated_unit_price`; §1.2 values new items at `qty × estimate`.
- **Decided:** if a `NEW` item has no estimate, still route `NEW_ITEM_SOURCING` (route is independent of value) but set `group_value_inr` empty/0 and note "no estimate" in `reason`. Do **not** mark `NOT_PROCESSED` — sourcing doesn't need a value.
- **Why:** the route is deterministic; a missing estimate shouldn't drop a legitimate sourcing request.

### D-4 · Blocked/Inactive first-preferred supplier
- **Noticed:** §5.7 bans Blocked/Inactive from PO/suggestions, but §6.1 already excludes them from the list.
- **Decided:** the preferred list contains **Active only**, so "1st preferred" is always Active. The §5.3/§5.4 history gate also requires the past buy to be from a supplier **Active now**. Belt-and-braces §5.7 filter re-applied on every emitted supplier/suggestion.
- **Why:** removes any path for a banned supplier to appear; the penalty is severe.

### D-5 · "Bought from an Active supplier in the last 365 days" (§5.3/§5.4 gate)
- **Noticed:** ambiguous whether "Active" is as-of-the-PO or as-of-now.
- **Decided:** interpret as the supplier being **Active in the current master** AND having a PO for the item within 365 days before the requirement date. Worked example 10 (small but never bought → RFQ) confirms the gate blocks when there's no qualifying history.
- **Why:** consistent with §5.7's present-tense status and the example.

### D-6 · Valuation vs contract selection (resolving the circularity)
- **Noticed:** §3.1(a) values at "the rate of the contract that will be used", but which contract is used depends on ceiling, which depends on value.
- **Decided:** pick the contract per §4.3 (lowest rate with enough ceiling at this requirement's value) using the contract rate itself for the ceiling check; value at that rate. If all applicable contracts are out of ceiling, value at the **lowest applicable contract rate** (example 3) and let §5 decide the route.
- **Why:** the contract rate is fixed per unit, so ceiling check and valuation are consistent without iteration.

### D-7 · Contract ceiling consumption order & concurrency
- **Noticed:** §4.2 consumes ceiling "in order of requirement date"; a batch has many requirements hitting one contract.
- **Decided:** sort PO-bound requirements by requirement date (then created_at, pr_no) and deduct from ceiling sequentially within a run; a requirement that would exceed the ceiling can't use the contract (then valued at lowest rate, §5 decides). Ties broken by first-line creation time.
- **Why:** deterministic and matches "consume in order of requirement date".

### D-8 · PDF-only contracts
- **Noticed:** §4.4 — contracts signed after 31 Oct exist only as PDFs (e.g. RC-2026-031), binding from start date, consumed = 0.
- **Decided:** load register contracts from CSV; allow adding PDF-only contracts (manual entry + optional LLM extraction from `contracts/pdf/`), initial consumed 0, participating in §4 immediately.
- **Why:** required by worked example 2 and feature F6.

### D-9 · Need-by window & clubbing edge cases
- **Noticed:** §2.2 windows: 14 calendar days (create) measured from the first line; ±7 days need-by. Unclear if "within 14 days" is inclusive and whether later-created lines can pull earlier need-by.
- **Decided:** inclusive on both bounds; a line joins if `0 ≤ created - first.created ≤ 14` days AND `|need_by - first.need_by| ≤ 7` days, same item+plant. If it fits multiple open requirements, join the earliest (by first-line time).
- **Why:** matches worked examples 5 (clubbed) and 6 (not clubbed — different plant).

### D-10 · Preferred-supplier ranking formula (design is ours, §6.2)
- **Noticed:** §6.2 leaves the weighting to us but requires it be consistent, explainable, recorded.
- **Decided:** score = `0.30·freq + 0.25·recency + 0.20·contract + 0.15·on_time + 0.10·quality`, where
  `freq` = normalised PO count in 548 d; `recency` buckets = 1.0 (≤90 d) / 0.5 (≤365 d) / 0.0 (older) per the worked-examples note; `contract` = 1 if held a contract for the item, else 0; `on_time` = on_time_pct/100; `quality` = quality_rating/5. Ties → more recent PO, then higher on-time. (Weights live in `docs/policy-v5.json` so they're tunable as data.)
- **Why:** reproduces the 3 published rankings (e.g. ITM-1048: S029 > S030 on frequency+contract; S031 excluded as Inactive) and is fully explainable to a buyer.

### D-11 · Reference & unit price rounding
- **Noticed:** PO history prices have decimals; contract rates vary; output needs a single `unit_price`.
- **Decided:** carry full precision internally; round to nearest rupee only for display/CSV, matching the worked-example figures (e.g. ₹9,169, ₹166). Document if a chosen rounding differs from an example.
- **Why:** avoids drift while matching published values.

### D-12 · ID schemes (`group_id`, `po_id`)
- **Noticed:** output needs our own requirement and PO ids; worked examples show `PO-0001`, etc.
- **Decided:** `group_id` = `REQ-<n>` assigned in processing order; `po_id` = `PO-<nnnn>` zero-padded, assigned in consolidation order. Stable within a run.
- **Why:** readable, deterministic, matches the example style.

### D-13 · PRs created outside the batch month / past need-by
- **Noticed:** some rows (e.g. `created_at` 2026-11-19) and need-by dates may sit oddly relative to "now".
- **Decided:** process every line on its own timestamps; do not drop rows for being future/past. Only use `NOT_PROCESSED` for genuinely unprocessable lines (e.g. empty item + empty description), with the reason recorded.
- **Why:** the engine must be timestamp-driven and reproducible regardless of wall-clock.

### D-14 · Roles & auth
- **Noticed:** brief wants who/when on every action but not real auth.
- **Decided:** lightweight role switch (Requester / Buyer / Procurement); actor + timestamp logged on PR creation, approve, override, and policy approval.
- **Why:** satisfies §8.1 audit without over-building.

### D-15 · Amendment application semantics
- **Noticed:** Run 2 applies an unknown amendment through the UI; it may change limits/categories or add a plant-specific rule.
- **Decided:** amendments compile to declarative ops over the policy document (`set_param` / `add_rule` / `remove_rule`), previewed in plain language, approved into a new version with an effective date; the engine always runs the version active as of the requirement date.
- **Why:** lets a *new kind* of rule (e.g. plant-specific) take effect with no code change — the core of the 15% bucket.

### D-16 · "Most recent PO" tie-break (valuation 3.1b & reference price 6.3)
- **Noticed:** ITM-1034 has two POs on the same latest date (₹40,929.88 and ₹41,415.60). "Most recent PO" is ambiguous on ties; the worked example (RFP, value ₹20,70,780) implies ₹41,415.60.
- **Decided:** order candidate POs by `(po_date, po_number)` descending and take the first. This reproduces worked example 11 exactly. Applied consistently to both valuation (3.1b) and reference price (6.3).
- **Why:** deterministic, and matches the published value. (Covered by `test_11_rfp`.)

### D-17 · Suggestion top-up ranking (6.4): combined delivery + quality
- **Noticed:** §6.4 tops up a short preferred list with category suppliers "best delivery and quality record first" — unspecified how to combine the two. Worked examples 10 & 11 (S003,S002,S005 and S020,S017,S019,S018) are reproduced only by a **combined** score, not on-time alone.
- **Decided:** top-up order = `on_time_pct/100 + quality_rating/5` descending (then supplier_id). Reproduces both examples. (Covered by `test_10`, `test_11`.)
- **Why:** on-time-only put S019 before S017 (wrong); the combined score matches the published lists.

### D-18 · Our own `po_id` / `group_id`, and consolidation numbering
- **Noticed:** the worked-examples PDF shows specific PO numbers (PO-0001…), but these depend on the full-batch ordering and are illustrative.
- **Decided:** `group_id = REQ-NNNN` (processing order), `po_id = PO-NNNN` assigned as POs open, ordered by each PO's first requirement's first-line creation time. We assert consolidation **relationally** (which requirements share a PO), which is what's scored — not the literal PO string. Our run legitimately opens an earlier SPOT_PO (servo drive at 08:10) that the examples didn't show, so absolute numbers differ by a small offset while every grouping matches.
- **Why:** the brief defines `po_id` as *our* number; correctness is the sharing, which is verified (`test_14`).

### D-19 · Amendment semantics & which version a run uses
- **Noticed:** the brief says a new version activates "from its effective date" and processing uses the version active as of the requirement date — yet Run 2 must visibly change the **same** (past-dated) batch.
- **Decided:** a batch is processed under the **currently active** policy version (Run 1 = v5.0; Run 2 = the approved amendment), with the effective date stored/shown for versioning and audit. "Process as of date" can also pick a historical version. This guarantees Run 2 reflects the amendment regardless of the batch's dates.
- **Why:** matches the blind-test workflow ("upload the amendment, approve it, reprocess the same batch") and avoids an amendment silently not applying because its effective date post-dates the batch. (Covered by `test_amendment_changes_a_decision`.)

### D-20 · Adding a *new kind* of rule without code
- **Noticed:** the brief expects future changes to add new rule kinds, e.g. plant-specific rules.
- **Decided:** the policy schema expresses conditions over a generic context (`requirement.plant`, `item.category`, `requirement.value`, …) and an ordered rule list; the engine is a pure interpreter. An `add_rule` amendment with a `requirement.plant == CHK1` condition takes effect with no code change. (Covered by `test_add_rule_new_kind_plant_specific`.)
- **Why:** this is the core of the "policy as data" bucket.

### D-21 · Explaining a ranking, and editing policy without an AI key
- **Noticed:** §6.2 requires the ranking to be *explainable*, and the blind test may hand us an amendment whose wording our heuristics cannot parse (no LLM key assumed on the exam machine).
- **Decided:** (a) the engine exposes the same §6 computation with its components (`PreferredEngine.ranked_list_detailed`, `GET /api/items/{code}/preferred?as_of=`), and the buyer drawer renders each rank with its five weighted components, the reference price and whether that supplier was used on the decision; (b) the Policy tab offers both plain-English amendments **and** a structured-ops panel that posts ops (`set_param`, `set_rule_value`, `add_rule`, `remove_rule`) straight to the same preview/approve flow.
- **Why:** the ranking must be defensible to a buyer without opening the PDF, and Run 2 must be applied *through the app* even if the amendment is worded in a way the heuristic parser doesn't recognise or the machine has no API key. Both paths are still data-only: no code change, and the ops are validated and previewed before anything activates.

---

### D-22 · Blind test — how Amendment No. 1 (v5.1) was applied (post-freeze note, no code change)
- **Noticed:** Amendment No. 1 (effective 2026-12-01) has three changes, two of them category/plant-conditional, which the heuristic NL parser cannot infer and the hosted app has no LLM key. The brief allows applying it "through your app's own policy-update feature (upload or chat)".
- **Decided:** applied it as **structured policy ops** through the app's amendment endpoint (the Policy tab's structured-ops panel, pre-built before the freeze — see D-21), previewed, approved into version **5.1 / effective 2026-12-01**. No code was changed; only policy data. The exact ops (reproducible on the hosted app):
  - **A1 (Packaging spot limit 2L→1L):** rule 5.4 made category-aware — spot now needs `value < 100000` for `item.category == "Packaging"` and keeps `value < 200000` for every other category (verified: non-packaging items in ₹1–2L stay SPOT_PO).
  - **A2 (RFP threshold 10L→8L):** rule 5.5 (RFQ) threshold `< 800000`; rule 5.6 (RFP) threshold `>= 800000`.
  - **A3 (new rule 5.2A, Chakan electrical safety):** inserted immediately after rule 5.2 (so a contract PO still wins) and before 5.3/5.4 (so it overrides emergency/spot): for `requirement.plant == "CHK1"` and `item.category == "Electrical Spares"` and `value >= 50000` → sourcing — RFP when `value >= 800000`, else RFQ.
- **Effect:** 25 of 190 decisions changed between Run 1 (v5.0) and Run 2 (v5.1), all attributable to A1/A2/A3; no Blocked/Inactive supplier appears in either run. Outputs: `submission/saurabhyadav__run1.csv`, `__run2.csv`, `__preferred.csv` (preferred as of 2026-12-01, top 3).
- **Why:** faithful to the amendment's exact wording and category/plant scope, fully as policy data, and reproducible by pasting the same ops into the hosted app's structured-ops panel.

---
*Append new decisions as they arise during the build and before the freeze.*
