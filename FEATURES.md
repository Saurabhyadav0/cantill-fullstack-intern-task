# FEATURES — what to build, with acceptance criteria

> Derived from the brief's 9 "Must have" items, mapped to the evaluation weights.
> Each feature has **acceptance criteria** (AC) that double as a definition of done.
> Priority: **P0** = required to score at all · **P1** = strongly scored · **P2** = polish.

Legend for the "Weight" column: which evaluation bucket the feature mainly earns (see `CONTEXT.md` §3).

---

## F1 — Policy-as-data engine *(P0 · Decisions 40% + Policy-as-data 15%)*

The core. A **pure, framework-independent** module that takes `(active_policy, PR batch, master data)` and returns decisions. No web/DB imports inside it.

**Sub-features**
- **F1.1 Item matching (§1):** code first; else fuzzy description match against item master. Returns a match **with confidence**; low confidence must be surfaced (chat asks; batch flags). Never invent an item. No match → `NEW`.
- **F1.2 Clubbing (§2):** group PR lines into requirements by the §2.2 rule (same item+plant, 14-day create window from first line, ±7-day need-by window, earliest wins). New items never clubbed.
- **F1.3 Valuation (§3.1):** contract rate (even if out of ceiling) → recent PO (365 d) → standard price.
- **F1.4 Contracts (§4):** applicability (dates inclusive, supplier Active), ceiling consumption in requirement-date order, lowest-rate-with-ceiling, PDF-only contracts start at consumed 0.
- **F1.5 Decision rules (§5):** ordered, first-match-wins, exactly as the table in `CONTEXT.md` §5.5. Capex checked first; §5.7 blocked/inactive guard everywhere.
- **F1.6 Preferred supplier list (§6):** eligibility, a **documented ranking formula**, reference price, suggestion top-up from category.
- **F1.7 PO consolidation (§7):** same supplier+plant+route within 24 h of the PO's first requirement; sourcing never combined.
- **F1.8 Reasoning trace:** every requirement carries the clause(s) applied + the contract/PO id relied on, for the `reason` column and the buyer UI.

**AC**
- [ ] Reproduces all 14 worked decisions (route, group, po consolidation, supplier, unit price, value) in an automated test, or divergence is justified in `DECISIONS.md`.
- [ ] Reproduces the 3 preferred-supplier rankings (order + reference price) as of 1 Nov 2026.
- [ ] Engine has **zero** references to the web framework or ORM; it takes plain data in, returns plain data out.
- [ ] Deterministic: same input + same policy ⇒ identical output.

---

## F2 — Versioned policy as data + amendment flow *(P0 · Policy-as-data 15%)*

Rules, limits, windows, rule order, conditions (item type, category, plant, value, urgency, contract, history) and outcomes are stored as a **versioned policy document** with an **effective date** — *not* as code.

**Sub-features**
- **F2.1 Policy schema:** a declarative document (see `docs/policy-v5.json`) with: parameters (clubbing windows, preferred-list windows, value thresholds), an **ordered rule list** (each rule = `conditions[] → outcome{decision, route, supplier_strategy}`), and the preferred-ranking weights. The engine is a generic **interpreter** of this schema.
- **F2.2 Versioning:** each policy is a row/version with `version`, `effective_date`, `status (draft/active/superseded)`, `created_by`, `created_at`, and the document body. Processing uses the version **active as of the requirement date**.
- **F2.3 Amendment intake:** Procurement uploads an amendment **document (PDF/text)** OR **describes the change in chat**. The app (LLM-assisted) parses it into a **structured diff** over the current policy.
- **F2.4 Plain-language preview + approve:** show *what will change* in plain English (e.g. "SPOT_PO limit ₹2,00,000 → ₹3,00,000; new rule: CHK1 emergencies ≤ ₹1,00,000 skip quotes"). On **approve**, create the new version effective from its date. Draft until approved.
- **F2.5 New *kinds* of rules without code:** the schema must express at least: a **plant-specific** condition, changed **category limits**, and an **added rule** — all data, no redeploy.

**AC**
- [ ] A changed limit (e.g. SPOT_PO threshold) alters outcomes after approval **without a code change** — provable by diffing Run 1 vs Run 2.
- [ ] A **brand-new rule** (e.g. "for plant CHK1, Emergency ≤ ₹1,00,000 → EMERGENCY_PO") can be added via the schema and takes effect.
- [ ] Old versions are retained; you can process "as of" any date and see which version applied.
- [ ] Amendment is applied entirely through the UI; commit history shows **no code change** at blind-test time.

---

## F3 — Chat intake (not forms) *(P0 · Chat & UX 20%)*

A requester types free text; the assistant resolves it into a clean PR.

**Sub-features**
- **F3.1 NL understanding:** parse "need 200 nitrile gloves for Chakan by next Friday" → item, qty, plant, need-by, urgency.
- **F3.2 Item resolution + disambiguation:** match to master; if ambiguous show candidates; if unknown, say so and offer `NEW` — **never fabricate** a code.
- **F3.3 Slot-filling:** ask only for genuinely missing/required fields (qty, plant, need-by, urgency), confirm, then create the PR.
- **F3.4 Batch upload:** accept a PR batch CSV in the sample format as an alternative to chat.
- **F3.5 Policy chat (Procurement):** same chat surface lets Procurement *describe* an amendment (feeds F2.3).

**AC**
- [ ] Vague item → asks a clarifying question instead of guessing.
- [ ] Unknown item → explicitly flagged as new, not invented.
- [ ] A complete utterance creates a valid PR with all required fields.
- [ ] CSV upload produces the same internal PR objects as chat.

---

## F4 — Buyer workspace *(P1 · Chat & UX 20% + Decisions 40%)*

Where buyers see and act on decisions.

**Sub-features**
- **F4.1 Requirements view:** each requirement with its PR lines, decision, route, value, supplier + price (or ranked suggestions), and **why** (clause, policy version, contract/PO used).
- **F4.2 One obvious next action per screen:** **Approve** → creates the PO or RFQ/RFP. **Override** → requires a comment.
- **F4.3 Audit log:** every action (who + when + before/after) retained, incl. overrides with reason (§8.1).
- **F4.4 Explainability:** buyer can see the preferred-list ranking rationale for any suggestion (why S029 ranks above S030).

**AC**
- [ ] Clicking Approve transitions the requirement to PO/RFQ/RFP and records actor + timestamp.
- [ ] Override without a comment is rejected.
- [ ] A buyer can read a decision and understand it in seconds without opening the policy PDF.

---

## F5 — API & export *(P0 · Decisions 40% + Engineering 10%)*

- **F5.1** `POST /api/process-batch` — takes a PR batch CSV, returns decisions (one object per PR line, output schema of `CONTEXT.md` §6).
- **F5.2** CSV export of decisions in exactly that column order.
- **F5.3** Preferred-supplier CSV export `item_code, rank, supplier_id, reference_price` (top 3) **as of a given date**.
- **F5.4** Supporting REST: policies (list/upload/preview/approve), requirements, suppliers, contracts.

**AC**
- [ ] `POST /api/process-batch` with the sample CSV returns rows matching the worked examples.
- [ ] Exported CSV headers/order match §6 exactly; `suggested_supplier_ids` is `;`-separated and ranked.
- [ ] Preferred export honours the "as of" date.

---

## F6 — Contracts management *(P1 · Decisions 40%)*

- **F6.1** Load the contract register + lines.
- **F6.2** Add a **PDF-only** contract — manual entry **or** extract fields from the signed PDF (LLM/parse). Must participate in §4 immediately.

**AC**
- [ ] `RC-2026-031`-style PDF-only contract can be added and then drives a `CONTRACT_PO` (worked example 2).
- [ ] Ceiling/consumption for a newly added contract starts at 0.

---

## F7 — Setup, hosting, delivery *(P0 for hosting · Engineering 10%)*

- **F7.1** `README.md` with **one-command local run** (`docker compose up` ideal).
- **F7.2** **Working hosted link** (Render/Railway/Vercel). Stays up through review; blind-test may be re-run on it.
- **F7.3** Seed script loads master data, contracts, PO history and the **v5.0 policy** locally (from the gitignored `data/`).
- **F7.4** Tests: engine unit tests against worked examples; a couple of API/integration tests.
- **F7.5** `DECISIONS.md` (judgment) + `APPROACH.md` (what AI tools were used) kept current.

**AC**
- [ ] Fresh clone + place data + `docker compose up` → app runs and the sample batch processes.
- [ ] Hosted link loads and can process a batch end-to-end.
- [ ] `pytest`/test runner is green on the worked-example suite.

---

## Non-goals / explicit scope limits
- No real authentication/SSO — a simple role switch (Requester / Buyer / Procurement) is enough; log the actor.
- No real email/ERP integration — "create PO/RFQ" is an internal state change + record.
- No GST/tax math — all values exclude GST per policy.
- Do **not** hard-code answers for specific PR numbers or items — the blind batch is different.

## Traceability — brief "Must have" → feature
1. Web app (FE+API+DB) → F4,F5,F7 · 2. Chat intake + CSV → F3 · 3. Policy as data → F2 · 4. Decision engine → F1 · 5. Preferred list → F1.6,F5.3 · 6. Buyer workspace → F4 · 7. API & export → F5 · 8. Contracts incl. PDF-only → F6 · 9. Setup + hosted → F7.
