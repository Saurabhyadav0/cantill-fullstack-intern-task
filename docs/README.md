# docs/ — policy schema (policy as data)

`policy-v5.json` is the **v5.0 procurement policy encoded as data** — the document the
engine interprets. It is **gitignored** (treated as task data; see the root `.gitignore`
and `DECISIONS.md` D-0), so it ships locally only. Place it here for local dev / seeding;
supply it at deploy time for hosting (same as `data/`).

## Policy document shape
```jsonc
{
  "version": "5.0",
  "effective_date": "2026-04-01",
  "parameters": {
    "clubbing":      { "create_window_days": 14, "need_by_window_days": 7, ... },
    "valuation":     { "recent_po_lookback_days": 365, ... },
    "contracts":     { "dates_inclusive": true, "supplier_must_be": "Active", ... },
    "preferred_list":{ "eligibility_lookback_days": 548, "ranking_weights": {...} },
    "consolidation": { "combine_window_hours": 24, "match_fields": [...] }
  },
  "supplier_guard": { "never_po_or_suggest_status": ["Blocked", "Inactive"] },
  "rules": [
    { "id": "5.1", "clause": "5.1", "name": "...",
      "when": { "all": [ {"field": "...", "op": "eq|lt|lte|gt|gte|exists|in", "value": ...} ] },
      "outcome": { "decision": "PO|SOURCING_REQUEST", "route": "...", "supplier_strategy": "...", "price": "..." } }
  ]
}
```

## Fields the rule conditions can reference
`item.item_type`, `item.category`, `requirement.plant`, `requirement.value`,
`requirement.is_emergency`, `requirement.urgency`, `requirement.usable_contract`,
`requirement.bought_from_active_supplier_within_365d`, `requirement.category`.

## Why this matters
Because the rule order, thresholds, windows and outcomes all live here, an amendment is
just a **new version of this document** (changed params, or an added/removed rule) approved
through the app — **no code change**. That is exactly what the blind-test Run 2 exercises.
Adding a *new kind* of rule (e.g. a `requirement.plant == CHK1` condition) needs no code.
