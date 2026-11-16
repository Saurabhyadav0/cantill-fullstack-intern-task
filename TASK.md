# TASK — build plan & checklist

> Execution plan to go from this scaffold to a submitted, hosted app by **Thu 19 Nov 10:00 IST**.
> ~3 working days. Priorities match `FEATURES.md`. Check boxes as you go.

## Recommended stack (chosen for speed + the "engine ≠ UI" grading)

| Layer | Choice | Why |
|---|---|---|
| Decision engine | **Pure Python package** (`engine/`), no web/DB imports | testable in isolation; reproduces worked examples; the 40% bucket |
| Backend API | **FastAPI** (Python) | fast to build, typed, auto OpenAPI; shares Python with the engine |
| DB | **PostgreSQL** (SQLite acceptable for local-only) | relational fits requirements/POs/contracts/audit; JSONB for the policy document |
| Frontend | **React + Vite + Tailwind** | quick chat + buyer workspace |
| LLM (chat + policy/PDF parsing) | **Claude** (`claude-sonnet-5-5` via Anthropic API) | NL intake, amendment→diff, PDF contract extraction. See `claude-api` skill for current model ids/pricing before wiring. |
| Deploy | **Railway** (Postgres + web) or Render; Vercel for a split FE | free tier, `docker compose up` locally |

> Swap any layer you're faster in — the engine purity and the output contract matter, not the framework. If you change stack, update `APPROACH.md`.

---

## Milestone 0 — Repo & skeleton *(½ day)*
- [ ] `git init`; push **public** repo. Keep `data/` and `docs/policy-v5*.json` gitignored (already configured).
- [ ] Monorepo layout:
  ```
  engine/        # pure decision engine (Python package) + policy interpreter
  api/           # FastAPI app, DB models, routes, seed script
  web/           # React app (chat, buyer workspace, policy admin)
  tests/         # engine unit tests (worked examples) + api tests
  docs/          # policy-v5.json (gitignored), schema docs
  data/          # gitignored kit data (local dev)
  submission/    # blind-test CSVs go here on Thu
  docker-compose.yml
  ```
- [ ] `docker-compose.yml`: db + api + web, one command up.
- [ ] `.env.example` (DB url, `ANTHROPIC_API_KEY`).

## Milestone 1 — Data model & loaders *(½ day)*
- [ ] DB schema: `items, suppliers, po_history, plants, contracts, contract_lines, policies(version, effective_date, status, body JSONB, created_by, created_at), requirements, pr_lines, pos, po_lines, audit_log`.
- [ ] Seed script loads all `data/*.csv` + seeds **policy v5.0** from `docs/policy-v5.json`.
- [ ] Parse dates/timestamps carefully (creation time drives clubbing & consolidation order).

## Milestone 2 — Decision engine + golden tests *(1 day — highest value)*
Build in pipeline order, testing each stage against `Worked_Examples.pdf`:
- [ ] **F1.1** item matching (code → fuzzy description). Encode the worked matches (e.g. `brg 6308 ZZ` → ITM-1022; `hyd hose 1/2 inch 2 wire` → ITM-1035).
- [ ] **F1.2** clubbing (§2.2) — order by created_at, PR no, line; windows 14 d / ±7 d; earliest wins.
- [ ] **F1.4 + F1.3** contracts & valuation together (valuation needs the chosen/least-rate contract). PDF-only contracts start consumed 0; ceiling consumed in requirement-date order.
- [ ] **F1.5** decision rules — ordered table, first match wins; §5.7 guard.
- [ ] **F1.6** preferred list + reference price + suggestion top-up.
- [ ] **F1.7** PO consolidation (§7) — same supplier+plant+route within 24 h; assign `po_id`.
- [ ] **Golden test** `tests/test_worked_examples.py`: assert all 14 decisions + 3 rankings. **This is your scoreboard for the 40%.**
- [ ] Emit the §6 output objects with `reason` + `policy_version`.

## Milestone 3 — Policy-as-data & amendment flow *(½–1 day — the 15% + blind-test Run 2)*
- [ ] Finalise `docs/policy-v5.json` schema; engine interprets it generically (no hard-coded thresholds).
- [ ] Amendment intake: upload doc **or** chat description → LLM → **structured diff**.
- [ ] Plain-language **preview** of the diff; **approve** → new version with effective date; drafts stay inactive.
- [ ] Prove a **new rule kind** works: add a **plant-specific** rule in the schema and see outputs change — no code edit.
- [ ] "Process as of date" selects the version active then.

## Milestone 4 — API & exports *(½ day)*
- [ ] `POST /api/process-batch` (CSV in → decisions out).
- [ ] CSV export (decisions, §6 column order) + preferred-supplier CSV ("as of" date).
- [ ] REST for policies/requirements/suppliers/contracts.

## Milestone 5 — Frontend *(1 day, parallelisable)*
- [ ] Chat intake with slot-filling + disambiguation (F3).
- [ ] Buyer workspace: requirements, decision + why, Approve / Override (comment required), audit (F4).
- [ ] Policy admin: upload/describe amendment → preview → approve; version history (F2).
- [ ] CSV upload + export buttons.

## Milestone 6 — Hosting, tests, docs *(½ day)*
- [ ] Deploy to Railway/Render; verify hosted batch processing end-to-end.
- [ ] `README.md`: one-command run + hosted link + architecture diagram.
- [ ] Fill `DECISIONS.md` (every assumption) and `APPROACH.md` (AI tools used).
- [ ] Green test suite. Tag the build-freeze commit.

---

## Blind-test runbook (Thu 19 Nov, 10:00–12:00 — NO code changes)
1. [ ] **Run 1:** upload new batch → process under **v5.0** → export → save as `yourname__run1.csv`.
2. [ ] **Run 2:** upload the **amendment** via policy admin → preview → **approve** → reprocess same batch → export → `yourname__run2.csv`.
3. [ ] Export preferred-supplier lists **as of the given date** → `yourname__preferred.csv`.
4. [ ] `git add submission/ && git commit && git push` **before 12:00 noon**. (Replace `yourname` with your actual name.)
5. [ ] Sanity: diff Run 1 vs Run 2 to confirm the amendment changed outcomes; grep outputs for any Blocked/Inactive `supplier_id` (must be none).

## Definition of done (submission)
- [ ] Public repo, **no task data files committed**, hosted link live.
- [ ] Sample batch reproduces the worked examples.
- [ ] Amendment works through the UI with no code change (commit history clean after freeze).
- [ ] `README.md`, `DECISIONS.md`, `APPROACH.md` complete.

## Risk watch
- **Clubbing/consolidation ordering bugs** — most common source of wrong `group_id`/`po_id`. Test hard.
- **Valuation circularity** (value ↔ contract choice) — resolve contract selection first, then value.
- **Blocked/inactive leakage** into suggestions — explicitly penalised; filter at every output.
- **Policy not truly data-driven** — if a threshold is a constant in code, Run 2 fails. Keep ALL limits in the policy document.
- **Hosted app sleeping** — free tiers idle; confirm it wakes before review.
