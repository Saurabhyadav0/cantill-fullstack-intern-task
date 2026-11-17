# APPROACH.md

How this was built, and which AI tools were used (required by the brief's ground rules).

## Architecture (as built)
```
engine/   PURE Python decision engine — no web, no DB, no network.
          models.py (dataclasses) · matching.py (item match, stdlib difflib) ·
          policy.py (generic interpreter over the policy document) ·
          core.py (pipeline: match → club → value+contract → decide → prefer → consolidate) ·
          loaders.py (CSV/JSON → models)
api/      FastAPI app. db.py (stdlib sqlite3: versioned policies, audit, added
          contracts, chat PRs, runs, overrides) · amend.py (amendment ops + plain-language
          preview + optional LLM) · chat.py (NL → PR, heuristic) · main.py (routes + serves UI)
web/      Single-file SPA (React 18 + htm + Tailwind via CDN) served by FastAPI:
          chat intake, buyer workspace, policy admin, contracts, audit.
tests/    25 tests: 14 worked decisions + 3 preferred rankings + invariants + API/blind-test loop.
```

**Why this shape.** The engine is deliberately pure so it is unit-testable against the
worked examples and cleanly separated from UI/IO (graded under Engineering). The web
framework is FastAPI; persistence is **stdlib sqlite3** (zero binary deps — robust on any
Python, incl. 3.15); the frontend is a no-build single file (reliable to host as one
service). Everything that is a policy knob (limits, windows, rule order, outcomes) lives in
the **policy document** (`docs/policy-v5.json`), interpreted generically — so an amendment
changes decisions with no code change.

## Decision engine pipeline (policy §1–§8)
item match (§1) → club into requirements (§2) → choose contract + value (§3,§4, ceiling
consumed in requirement-date order) → ordered decision rules, first match wins (§5, with the
§5.7 Blocked/Inactive guard) → preferred list + suggestions (§6) → PO consolidation (§7) →
emit rows with clause + policy version (§8). Reproduces all 14 worked decisions and the 3
preferred-supplier rankings exactly (see `tests/`).

## Policy as data
Versioned documents in SQLite (`version`, `effective_date`, `status`, body JSONB). An
amendment is parsed (structured ops, a heuristic NL parser, or Claude if a key is set) into
ops over the document, previewed in plain language, and approved into a new active version.
Supports changed limits, changed windows, and **adding a new kind of rule** (e.g.
plant-specific) — all as data.

## AI tools used
- **Claude Code (Opus 4.8)** — built the engine, API, frontend, tests, and docs; iterated the
  engine against the worked examples until all 14 + 3 reproduced.
- **Claude API (`claude-sonnet-5-5`)** — *optional, inside the app*: if `ANTHROPIC_API_KEY`
  is set, Claude parses a free-text amendment document into policy ops (`api/amend.py`). The
  app is fully functional without it (heuristic parsers cover chat intake and common
  amendments).

> I can explain and change every part of the code. The engine is small and clause-by-clause,
> so each policy rule maps to a test.

## What I'd add with more time
PDF text-extraction for contract auto-fill (currently manual entry / seeded from the PDFs),
a richer disambiguation UI, per-supplier ranking-explanation panel, and more integration tests.
