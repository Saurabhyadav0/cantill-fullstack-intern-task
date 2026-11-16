# CONTEXT — Cantill.ai Full-stack Intern Task

> Single source of truth for **what the app must do and why**. Read this before writing code.
> Pair it with `FEATURES.md` (what to build), `TASK.md` (the build plan), and `CLAUDE.md` (engine invariants for AI-assisted coding).

---

## 1. One-line brief

Build a web app where employees raise purchase requests **by chatting**, and the system decides — **by following the company's procurement policy stored as data** — whether to place a **Purchase Order (PO)** or raise a **Sourcing request**. When Procurement uploads a new policy version, the app's decisions must change **with no code change**.

- **Company:** Corvo Engineering Pvt Ltd (fictional engineering manufacturer).
- **Plants:** `PUN1` (Pune – Bhosari), `CHK1` (Chakan).
- **Policy in force:** Procurement Policy **v5.0**, effective 1 April 2026. All values in **INR, excluding GST**.
- **Build deadline:** Thu 19 Nov 2026, 10:00 IST (today is Mon 16 Nov — ~3 days).
- **Repo:** public GitHub, **must not contain the task data files**. Hosted link required and must stay up.

## 2. Timeline & the blind test (this shapes the architecture)

| When (IST) | What |
|---|---|
| Mon 16 Nov | Kit received. |
| **Thu 19 Nov 10:00** | **Build freeze.** Submit public repo + hosted link. Last commit before this = frozen app. |
| Thu 19 Nov 10:00 | We email a **new PR batch** + a **policy amendment**. |
| Thu 19 Nov 12:00 | **Blind-test deadline.** Push 3 CSVs into `submission/`. Files after noon, or any code change after 10:00, are not scored. |

**Blind-test runs (no code changes allowed):**
- **Run 1:** process the new batch under **v5.0** → export decisions → `yourname__run1.csv`.
- **Run 2:** upload the **amendment** through the app's own policy-update feature, approve it, reprocess the same batch → `yourname__run2.csv`. Also export preferred-supplier lists as of a given date → `yourname__preferred.csv`.

> **Design consequence:** the policy engine must be a pure interpreter over a versioned policy **document (data)**. The amendment is applied at runtime through the UI — never by editing code. Expect the amendment to **change category rules & limits** and to **add a new kind of rule (e.g. plant-specific)**.

## 3. How it is evaluated (build to the weights)

| Part | Weight | Focus |
|---|---|---|
| Decisions (automated) | **40%** | Run 1 & Run 2 accuracy: route, clubbing, PO consolidation, item matching, values, suppliers & prices, suggestions; amendment took effect; preferred lists. **Using a Blocked/Inactive supplier is penalised.** |
| Policy as data | **15%** | How changes are captured, shown, approved, versioned, dated; can a *new kind of rule* be added without code. |
| Chat intake & UX | **20%** | Right follow-up questions, no inventing items; buyer can understand & act on each decision fast. |
| DECISIONS.md & judgment | **15%** | Did you notice gaps in the policy and decide sensibly? Is supplier ranking well reasoned? |
| Engineering & delivery | **10%** | Data model, API, engine/UI separation, tests, README, hosted demo. |

Round 2 (shortlist): walk through the app + `DECISIONS.md`, and **make a change live**.

---

## 4. Domain glossary

- **PR line** — one requested item on a purchase requisition (the raw input row).
- **Requirement (group)** — one or more PR lines **clubbed** together and judged as a unit. `group_id` identifies it.
- **Route** — the specific outcome type: `CONTRACT_PO`, `EMERGENCY_PO`, `SPOT_PO`, `RFQ`, `RFP`, `CAPEX_SOURCING`, `NEW_ITEM_SOURCING` (+ `NOT_PROCESSED` for lines you choose to skip).
- **Decision** — coarse outcome: `PO` or `SOURCING_REQUEST`.
- **Rate contract** — a standing contract that fixes a supplier's rate for an item, with a value **ceiling**.
- **Preferred supplier list** — per-item ranking built automatically from PO history + contracts.
- **Reference price** — the price used for a preferred-supplier PO (see 6.3).

---

## 5. The policy, encoded precisely (v5.0)

> This is the authoritative restatement the engine must implement. Clause numbers match the PDF.
> The machine-readable version lives in `docs/policy-v5.json` (gitignored). **Rule order matters.**

### 5.1 Identify the item (§1)
- **§1.1** Every PR line matches an item in the item master. If `item_code` is given, use it. Otherwise match the **description** (requesters use short forms, e.g. `brg 6205 2rs` → *Ball bearing 6205-2RS*).
- **§1.2** No match ⇒ **new item**: route `NEW_ITEM_SOURCING`, **never clubbed**, valued at `quantity × requester's estimated unit price`, **no supplier suggestions**.
- ⚠️ *Capex is detected from the matched master item's `item_type`, not from the text.* A vague phrase like "eot crane 5 ton" that **matches** a Capex master item → `CAPEX_SOURCING`, not `NEW_ITEM_SOURCING` (worked example 12). `NEW` only when there is genuinely no match.

### 5.2 Club requirements — no splitting (§2)
- **§2.1** Splitting to stay under a limit is banned. Apply **every limit to the requirement's total value**.
- **§2.2** Process PR lines in order of **creation time → PR number → line number**. A line **joins** an existing requirement when ALL hold:
  - same **item** (resolved code), AND
  - same **plant**, AND
  - created **within 14 calendar days** of the requirement's **first** line, AND
  - its **need-by date within ±7 days** of the first line's need-by.
  - If it could join more than one, it joins the **earliest**. Otherwise it starts a new requirement.
- **§2.3** Requirement date = creation date of its **first** line. Contract validity & purchase history are checked **as of this date**. If **any** line is `Emergency`, the requirement is an emergency.

### 5.3 Value the requirement (§3)
- **§3.1** `value = total_quantity × unit_price`, where `unit_price` = **first available** of:
  1. the **rate of the contract that will be used** (§4.3); or, if **every applicable contract is out of ceiling**, the **lowest applicable contract rate**;
  2. the price on the **most recent PO** for the item in the **365 days before** the requirement date;
  3. the **item master standard price**.
- ⚠️ Even a contract that is *out of ceiling* still sets the value via rule (a) (worked example 3: bearings valued at the lowest contract rate although the contract can't be used).

### 5.4 Contracts (§4)
- **§4.1** A contract **applies** if: it covers the item, requirement date is **within [start, end] inclusive**, and the contract supplier is **Active**.
- **§4.2** Usable only while **ceiling left**: `consumed_value + this_requirement_value(at contract rate) ≤ value_cap`. Requirements consume ceiling **in order of requirement date**. Register `consumed_value` is as at its last update (31 Oct 2026); **PDF-only contracts signed after that start at consumed = 0**.
- **§4.3** If several apply, use the **lowest rate** that still has enough ceiling.
- **§4.4** Register is updated monthly. Contracts signed after the last update exist **only as signed PDFs** and are binding from their **start date** (worked example 2: `RC-2026-031` applies although not in the register).

### 5.5 Decision rules — first match wins, in order (§5)

| # | Condition | Decision | Route | Supplier & price |
|---|---|---|---|---|
| **5.1** | matched item `item_type = Capex` | SOURCING | `CAPEX_SOURCING` | suggest **5** (§6.4); needs capex approval |
| **5.2** | a contract **can be used** (§4.1–4.3) | PO | `CONTRACT_PO` | contract supplier at **contract rate** |
| **5.3** | **Emergency** AND value **≤ ₹5,00,000** AND item bought from an **Active** supplier in last **365 days** | PO | `EMERGENCY_PO` | **1st preferred** at reference price |
| **5.4** | value **< ₹2,00,000** AND item bought from an **Active** supplier in last **365 days** | PO | `SPOT_PO` | **1st preferred** at reference price |
| **5.5** | value **< ₹10,00,000** (incl. small items never bought in 365 d) | SOURCING | `RFQ` | suggest **3** (§6.4) |
| **5.6** | value **≥ ₹10,00,000** | SOURCING | `RFP` | suggest **5** (§6.4) |

- **§5.7** Blocked or Inactive suppliers must **never** receive a PO or be suggested. (Penalised if violated.)
- ⚠️ §5.2 beats value limits — a contract item is a `CONTRACT_PO` whatever the value (worked example 1).
- ⚠️ The §5.3/§5.4 gate is "bought from an **Active** supplier in the last 365 days" — if never bought (or only from inactive/blocked), these PO routes do **not** apply and it falls to RFQ/RFP (worked example 10).

### 5.6 Preferred supplier list (§6) — *recalculated as of each requirement date*
- **§6.1 Who is on it:** every **Active** supplier with either (a) ≥1 PO for the item in the **548 days** before the date, OR (b) a contract covering the item **started on/before** the date (even if since expired).
- **§6.2 Ranking:** best choice for a direct PO first. Consider: **how often** bought, **how recently**, **held a contract** for the item, **on-time %** and **quality rating**. Weighting is **your design** — must be consistent, explainable, recorded in `DECISIONS.md`. Top = **1st preferred supplier**.
- **§6.3 Reference price:** that supplier's most recent PO price for the item in 548 days; if none, the rate in its most recent contract for the item.
- **§6.4 Suggestions for sourcing:** take the preferred list in order; if shorter than needed (3 or 5), top up with other **Active** suppliers that list the item's **category**, best on-time/quality first. **New items get no suggestions.**
- Export columns: `item_code, rank, supplier_id, reference_price` (top 3) as of a chosen date.

### 5.7 PO consolidation (§7)
- **§7.1** Requirements that end in a PO combine into **one PO with several lines** when they share **same supplier + same plant + same route**, and were raised **within 24 hours** of the first requirement on that PO (measured from each requirement's **first line creation time**).
- **§7.2** Take requirements in creation order; join the **earliest open PO** that qualifies, else start a new PO. **Sourcing requests are never combined.**

### 5.8 Record keeping (§8)
- **§8.1** Every decision records the **policy clause** applied and the **contract/PO** relied on. Overrides require a **written reason**, kept with the original. Every action logs **who + when**.

---

## 6. Output format (the scored CSV — one row per PR line)

| Column | Content |
|---|---|
| `pr_no`, `pr_line` | as in input |
| `resolved_item_code` | matched code, or `NEW` |
| `group_id` | requirement ID; clubbed lines share it |
| `po_id` | PO number for lines ending in a PO; consolidated requirements share it |
| `decision` | `PO` or `SOURCING_REQUEST` |
| `route` | one of the 7 routes (+ `NOT_PROCESSED`) |
| `supplier_id`, `unit_price` | for POs |
| `group_value_inr` | value of the whole requirement |
| `suggested_supplier_ids` | for sourcing, ranked, `;`-separated |
| `policy_version`, `reason` | version + clause applied, and the contract/PO relied on |

`NOT_PROCESSED` is for lines you deliberately skip — record why in `DECISIONS.md` and in `reason`.

---

## 7. Data the engine reads (local only — `data/`, gitignored)

All fictional. Columns as shipped:

- **`master_data/item_master.csv`** (73) — `item_code, description, uom, category, item_type, standard_price`. `item_type ∈ {Material, …, Capex}`.
- **`master_data/supplier_master.csv`** (48) — `supplier_id, name, city, categories, status, on_time_pct, quality_rating`. `status ∈ {Active, Inactive, Blocked}`.
- **`master_data/po_history.csv`** (~468) — `po_number, po_date, supplier_id, item_code, quantity, uom, unit_price, plant, delivered_on_time`. June 2025 → Oct 2026.
- **`master_data/plants.csv`** — `plant, name` (PUN1, CHK1).
- **`contracts/contract_register.csv`** (10) — `contract_id, supplier_id, supplier_name, start_date, end_date, value_cap, consumed_value` (as at 31 Oct 2026).
- **`contracts/contract_lines.csv`** (26) — `contract_id, item_code, description, uom, rate`.
- **`contracts/pdf/*.pdf`** — signed copy of every contract; **some exist only here** (signed after the register update) and must be loadable (manual entry or PDF extraction).
- **`pr_batches/sample_pr_batch.csv`** (186) — `pr_no, pr_line, created_at, requester, department, plant, item_code, description, quantity, uom, estimated_unit_price, need_by_date, urgency`.

> `data/` and the policy JSON are **gitignored**. The public repo ships schema/examples only — see `data/README.md`.

## 8. Worked examples = the acceptance fixtures

The 14 worked decisions + 3 preferred-supplier rankings in `Worked_Examples.pdf` are the **golden tests**. The engine must reproduce them exactly (or you must explain any deliberate divergence in `DECISIONS.md`). Key ones they isolate: contract-beats-value (1), PDF-only contract (2), ceiling exhausted (3), lowest-rate-with-ceiling across two contracts (4), clubbing (5), not-clubbed-different-plant (6), free-text match (7), emergency PO (8), RFQ above PO limit (9), small-but-never-bought → RFQ (10), RFP (11), capex (12), new item (13), PO consolidation (14).

See `TASK.md` → "Milestone 2" for turning these into automated tests.
