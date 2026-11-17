# data/ — local only, NOT committed

The task requires the **public repo to contain no task data files**. So everything the kit shipped
stays here and is **gitignored** (see `.gitignore`). This README is the only committed file in `data/`.

## What goes here (copy from the kit: `Cantill_FullStack_Task_Kit/`)
```
data/
  master_data/
    item_master.csv          # 73 items
    supplier_master.csv      # 48 suppliers (status, on_time_pct, quality_rating)
    po_history.csv           # ~468 POs, Jun 2025 – Oct 2026
    plants.csv               # PUN1, CHK1
  contracts/
    contract_register.csv    # 10 contracts (as at 31 Oct 2026)
    contract_lines.csv       # 26 contract line rates
    pdf/                      # signed copy of every contract (some PDF-only)
  pr_batches/
    sample_pr_batch.csv      # 186 PR lines, Nov 2026
  Corvo_Procurement_Policy.pdf
  Worked_Examples.pdf
  Cantill_FullStack_Task_Brief.pdf
```
Also keep `docs/policy-v5.json` locally (gitignored) — the v5.0 policy encoded as data, seeded into the DB.

## Setup
```bash
# from repo root, with the kit extracted somewhere:
KIT=~/Downloads/Cantill_FullStack_Task_Kit
cp -R "$KIT"/master_data data/
cp -R "$KIT"/contracts   data/
cp -R "$KIT"/pr_batches  data/
cp "$KIT"/*.pdf          data/
```
The seed script reads from here. Column schemas are documented in `CONTEXT.md` §7.

> Blind-test batch + amendment arrive Thu 19 Nov 10:00 — drop them here (or upload via the app) and
> process. The amendment is applied through the app's policy-update feature, never by editing code.
