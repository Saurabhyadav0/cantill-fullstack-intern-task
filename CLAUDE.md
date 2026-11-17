# CLAUDE.md — guardrails for AI-assisted work on this repo

AI coding is **allowed** for this task (record tools used in `APPROACH.md`). This file keeps any AI session accurate. Read `CONTEXT.md` first.

## Golden rules (do not break)
1. **Policy lives in data, never in code.** Every threshold, window, rule order and outcome comes from the active policy document (`docs/policy-v5.json` schema). If you're about to write `if value < 200000`, stop — read it from the policy instead. The blind-test Run 2 fails otherwise.
2. **Engine stays pure.** `engine/` imports no web framework and no ORM. Plain data in → plain data out. UI/API/DB sit around it.
3. **Never invent items or suppliers.** Unknown item → `NEW`. Ambiguous → ask (chat) or flag (batch).
4. **Never PO or suggest a Blocked/Inactive supplier** (§5.7). Filter at every output. This is explicitly penalised.
5. **Don't hard-code answers** for any PR number or item. The blind batch differs from the kit.
6. **Worked examples are the test oracle.** Change engine logic → run `tests/test_worked_examples.py`. All 14 decisions + 3 rankings must stay green (or justify divergence in `DECISIONS.md`).
7. **No committing task data.** `data/` and `docs/policy-v5*.json` are gitignored. Keep it that way.

## Pipeline order (must be exactly this)
item match (§1) → club into requirements (§2) → pick contract + value (§3,§4) → apply ordered decision rules (§5, first match) → build preferred list / suggestions (§6) → consolidate POs (§7) → emit rows with clause + policy_version in `reason` (§8).

## Easy-to-get-wrong details
- §5.2 (contract) beats all value limits. §5.1 (Capex) is checked before everything.
- Valuation uses the contract rate **even if the contract is out of ceiling** (then it can't be *used*, but it still sets value).
- §5.3/§5.4 require "bought from an **Active** supplier in last 365 days" — else fall through to RFQ/RFP.
- Clubbing: order by `created_at, pr_no, pr_line`; windows are 14 d (create, from first line) and ±7 d (need-by). Different plant ⇒ not clubbed. New items ⇒ never clubbed.
- Consolidation window (24 h) is anchored to the PO's **first** requirement's first-line time; sourcing never consolidates.
- Dates in contract validity are **inclusive**. "As of requirement date" = first line's creation date.
- Preferred list uses **548-day** windows; recency buckets 90 d / 365 d (see `DECISIONS.md` D-10).

## When the policy is silent
Make a sensible business call, implement it, and **record it in `DECISIONS.md`** (what you noticed, decided, why). Judgment is 15% of the score.

## House rules
- Keep commits meaningful; the examiners read commit history to confirm **no code change after the build freeze**.
- Do not add `Co-Authored-By` trailers.
- Prefer small pure functions per policy clause so each maps to a test.
