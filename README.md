# Corvo Engineering — Policy-driven PR→PO App

Employees raise purchase requests **by chatting**; the app decides — by following the
**procurement policy stored as data** — whether to place a **Purchase Order** or raise a
**Sourcing request**. When Procurement uploads a new policy version, decisions change **with
no code change**.

> Cantill.ai Full-stack Intern task, Round 1. Full context in `CONTEXT.md`; scope in
> `FEATURES.md`; plan in `TASK.md`; judgment calls in `DECISIONS.md`; tools in `APPROACH.md`.

## Repository
➡️ https://github.com/Saurabhyadav0/cantill-fullstack-intern-task — public, and it contains
no task data (see `.gitignore` and `DECISIONS.md` D-0).

## Hosted demo
➡️ **https://cantill-pr-po-latest.onrender.com**  _(free tier — first load may take ~30–60s to wake)_

Runs with **no environment variables**. (Optional: set `ANTHROPIC_API_KEY` to enable
LLM-assisted amendment parsing — the app is fully functional without it.)

## What works
- **Chat intake** — "need 200 nitrile gloves for Chakan by next Friday" → matches ITM-1048,
  fills qty/plant/need-by/urgency, asks when unsure, never invents an item (unknown → NEW).
- **Decision engine** (pure, policy §1–§8) — reproduces all **14 worked decisions** and the
  **3 preferred-supplier rankings** exactly. Item match · clubbing · valuation · contracts &
  ceilings · ordered decision rules · preferred list · PO consolidation.
- **Policy as data** — versioned policy documents; upload/describe an amendment → plain-language
  preview → approve → new active version. Supports changed limits/windows and **new kinds of
  rules** (e.g. plant-specific) with no code change.
- **Buyer workspace** — requirements with decision, value, supplier/price or ranked suggestions,
  and the **why** (clause + version + contract/PO). Approve creates the PO/RFQ; Override needs a
  reason; every action is audited.
- **Explainable preferred lists** — the drawer shows the §6 ranking with the score behind each
  position (frequency · recency · contract · on-time · quality), the weights read from the policy
  document, and which of those suppliers the decision actually used.
- **Amendments two ways** — describe the change in plain English, or apply **structured ops** in the
  UI when it is a brand-new kind of rule (e.g. plant-specific). Neither needs an AI key or a deploy.
- **API & exports** — `POST /api/process-batch`; `decisions.csv`; `preferred.csv?as_of=`.
- **Contracts** — register loaded; add a PDF-only contract (manual entry), used immediately.

## Quick start

### Option A — Docker (one command)
```bash
# Place the kit data + policy locally first (NOT committed — see data/README.md, docs/README.md)
docker compose up --build        # → http://localhost:8000
```

### Option B — Python
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000      # → http://localhost:8000
```
Optional: `cp .env.example .env` and set `ANTHROPIC_API_KEY` to enable LLM-assisted amendment
parsing (the app works fully without it).

> The public repo contains **no task data files**. Put the kit's `master_data/`, `contracts/`,
> `pr_batches/` under `data/`, and the policy at `docs/policy-v5.json` (see those folders' READMEs).

## Tests
```bash
pip install pytest httpx
pytest        # 25 tests: 14 worked decisions + 3 preferred rankings + invariants + API/blind-test
```

## Key API
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/process-batch` | PR batch CSV (or `source=sample\|stored`) → decisions |
| GET | `/api/export/decisions.csv` | decisions CSV (output schema, `CONTEXT.md` §6) |
| GET | `/api/export/preferred.csv?as_of=YYYY-MM-DD` | preferred suppliers (`item_code,rank,supplier_id,reference_price`) |
| POST | `/api/policies/amendment` | describe/upload an amendment → preview + draft version |
| POST | `/api/policies/{id}/approve` | activate a new policy version |
| POST | `/api/chat/parse` | free-text request → structured PR + candidates + missing slots |
| GET | `/api/requirements` · POST `.../approve` · `.../override` | buyer workspace |
| GET | `/api/contracts` · POST `/api/contracts` | contracts incl. PDF-only |

## Architecture
`engine/` is a **pure** Python package (no web/DB/network) interpreting a **versioned policy
document**; `api/` (FastAPI + stdlib sqlite3) wraps it with persistence, amendments, exports
and audit; `web/` is a single-file React/Tailwind SPA served by the API. See `APPROACH.md`.

## Blind-test runbook (Thu 19 Nov, 10:00–12:00 — no code changes)
1. **Run 1:** Buyer workspace → upload the new batch → process under v5.0 → `⬇ decisions.csv`
   → save as `yourname__run1.csv`.
2. **Run 2:** Policy tab (role = Procurement) → paste/describe the amendment → **Preview** →
   **Approve & activate** → Buyer workspace → reprocess the same batch → `⬇ decisions.csv` →
   `yourname__run2.csv`. Then `⬇ preferred.csv` as of the given date → `yourname__preferred.csv`.
3. Put the three files in `submission/` and push **before 12:00 noon**.

## Layout
```
engine/  pure decision engine (policy interpreter) + loaders
api/     FastAPI app, sqlite persistence, amendments, chat, exports
web/     single-file SPA (chat · buyer · policy · contracts · audit)
docs/    policy-v5.json (gitignored) + schema README
data/    kit data (gitignored, local dev)
tests/   engine + API tests
submission/  blind-test CSVs
```
All company, supplier and item data is fictional.
