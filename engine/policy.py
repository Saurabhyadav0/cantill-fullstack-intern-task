"""Policy-as-data: a generic interpreter over a versioned policy document.

The engine reads thresholds, windows, rule order and outcomes from this document,
never from code. An amendment is simply a new version of the document (changed
params, or added/removed rules) approved through the app. This is what lets the
blind-test Run 2 change decisions with no code change.
"""
from __future__ import annotations

import json
from typing import Any


class Policy:
    def __init__(self, doc: dict):
        self.doc = doc
        self.version = str(doc.get("version", "?"))
        self.effective_date = doc.get("effective_date")
        self.params = doc.get("parameters", {})
        self.rules = doc.get("rules", [])
        self.supplier_guard = doc.get("supplier_guard", {})

    # ---- parameter accessors (with policy-v5 defaults) -------------------- #
    @property
    def clubbing(self) -> dict:
        return self.params.get("clubbing", {})

    @property
    def valuation(self) -> dict:
        return self.params.get("valuation", {})

    @property
    def contracts(self) -> dict:
        return self.params.get("contracts", {})

    @property
    def preferred(self) -> dict:
        return self.params.get("preferred_list", {})

    @property
    def consolidation(self) -> dict:
        return self.params.get("consolidation", {})

    def guard_statuses(self) -> list:
        return self.supplier_guard.get("never_po_or_suggest_status", ["Blocked", "Inactive"])

    # ---- rule evaluation -------------------------------------------------- #
    def first_matching_rule(self, context: dict):
        """Return the first rule whose conditions all match, or None."""
        for rule in self.rules:
            if _eval_when(rule.get("when", {}), context):
                return rule
        return None

    @classmethod
    def from_json(cls, text: str) -> "Policy":
        return cls(json.loads(text))

    @classmethod
    def from_file(cls, path: str) -> "Policy":
        with open(path, "r", encoding="utf-8") as f:
            return cls(json.load(f))


# --------------------------------------------------------------------------- #
# Condition evaluation
# --------------------------------------------------------------------------- #
def _get(context: dict, path: str) -> Any:
    """Resolve a dotted path like 'requirement.value' against the context dict."""
    cur = context
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
        if cur is None:
            return None
    return cur


def _cmp(op: str, left: Any, value: Any) -> bool:
    if op == "exists":
        return left is not None and left is not False
    if op == "not_exists":
        return left is None or left is False
    if left is None:
        return False
    if op == "eq":
        return left == value
    if op == "neq":
        return left != value
    if op == "lt":
        return left < value
    if op == "lte":
        return left <= value
    if op == "gt":
        return left > value
    if op == "gte":
        return left >= value
    if op == "in":
        return left in (value or [])
    if op == "not_in":
        return left not in (value or [])
    raise ValueError(f"unknown operator: {op}")


def _eval_one(cond: dict, context: dict) -> bool:
    left = _get(context, cond["field"])
    return _cmp(cond.get("op", "eq"), left, cond.get("value"))


def _eval_when(when: dict, context: dict) -> bool:
    if not when:
        return True
    if "all" in when:
        return all(_eval_when(c, context) if ("all" in c or "any" in c) else _eval_one(c, context)
                   for c in when["all"])
    if "any" in when:
        return any(_eval_when(c, context) if ("all" in c or "any" in c) else _eval_one(c, context)
                   for c in when["any"])
    # a bare condition
    return _eval_one(when, context)
