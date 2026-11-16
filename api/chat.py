"""Chat intake: turn a free-text request into a structured PR line.

Heuristic parser (works with no network). Resolves item via the engine matcher and
reports missing slots so the UI can ask follow-ups instead of inventing data. If
ANTHROPIC_API_KEY is set it can defer to Claude, but the heuristics cover the demo.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from engine.matching import NEW, normalize
from engine.matching import _score as match_score

_PLANTS = {
    "chakan": "CHK1", "chk1": "CHK1",
    "bhosari": "PUN1", "pune": "PUN1", "pun1": "PUN1",
}
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_NOISE = re.compile(r"\b(need|want|require|please|pls|raise|pr|for|by|the|a|an|urgent|urgently|"
                    r"asap|emergency|plant|nos|pcs|units?|qty|quantity|approx|around|about)\b", re.I)


def _find_qty(text):
    m = re.search(r"\b(\d+(?:\.\d+)?)\b", text)
    return float(m.group(1)) if m else None


def _find_plant(text):
    t = text.lower()
    for k, v in _PLANTS.items():
        if k in t:
            return v
    return None


def _find_urgency(text):
    return "Emergency" if re.search(r"\b(emergency|urgent|asap|breakdown)\b", text, re.I) else "Normal"


def _find_need_by(text, today=None):
    today = today or date.today()
    t = text.lower()
    # explicit ISO or dd/mm
    m = re.search(r"(\d{4}-\d{2}-\d{2})", t)
    if m:
        return m.group(1)
    m = re.search(r"\bin\s+(\d+)\s+days?\b", t)
    if m:
        return (today + timedelta(days=int(m.group(1)))).isoformat()
    m = re.search(r"\bnext\s+(" + "|".join(_WEEKDAYS) + r")\b", t)
    if m:
        wd = _WEEKDAYS.index(m.group(1))
        delta = (wd - today.weekday()) % 7
        delta = delta + 7 if delta <= 0 else delta + 7   # "next" => following week
        return (today + timedelta(days=delta)).isoformat()
    m = re.search(r"\bby\s+(" + "|".join(_WEEKDAYS) + r")\b", t)
    if m:
        wd = _WEEKDAYS.index(m.group(1))
        delta = (wd - today.weekday()) % 7 or 7
        return (today + timedelta(days=delta)).isoformat()
    if "tomorrow" in t:
        return (today + timedelta(days=1)).isoformat()
    return None


def _item_phrase(text):
    """Strip qty/plant/date/noise words to isolate the item description."""
    t = text
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", t)
    t = re.sub(r"\bnext\s+\w+\b", " ", t, flags=re.I)
    t = re.sub(r"\bby\s+\w+\b", " ", t, flags=re.I)
    t = re.sub(r"\bin\s+\d+\s+days?\b", " ", t, flags=re.I)
    for k in _PLANTS:
        t = re.sub(r"\b" + k + r"\b", " ", t, flags=re.I)
    t = re.sub(r"\b\d+(?:\.\d+)?\b", " ", t)      # numbers (qty)
    t = _NOISE.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip(" .,-")
    return t


def candidates(phrase, items, k=3):
    scored = sorted(((it, match_score(phrase, it.description)) for it in items),
                    key=lambda x: x[1], reverse=True)[:k]
    return [{"item_code": it.item_code, "description": it.description,
             "category": it.category, "item_type": it.item_type,
             "score": round(s, 2)} for it, s in scored]


def parse(text: str, md, today=None):
    """Return a structured interpretation + missing slots + item candidates."""
    phrase = _item_phrase(text)
    cands = candidates(phrase, md.items) if phrase else []
    best = cands[0] if cands else None
    confident = bool(best and best["score"] >= 0.55)
    ambiguous = bool(len(cands) >= 2 and cands[0]["score"] - cands[1]["score"] < 0.06
                     and cands[0]["score"] >= 0.55)

    qty = _find_qty(text)
    plant = _find_plant(text)
    need_by = _find_need_by(text, today)
    urgency = _find_urgency(text)

    missing = []
    if not confident:
        missing.append("item")
    if qty is None:
        missing.append("quantity")
    if not plant:
        missing.append("plant")
    if not need_by:
        missing.append("need_by_date")

    return {
        "interpretation": {
            "item_phrase": phrase,
            "resolved_item_code": best["item_code"] if confident else None,
            "resolved_description": best["description"] if confident else None,
            "quantity": qty, "plant": plant, "need_by_date": need_by, "urgency": urgency,
        },
        "candidates": cands,
        "confident_item": confident,
        "ambiguous": ambiguous,
        "missing": missing,
        "is_new_candidate": bool(phrase and (not best or best["score"] < 0.55)),
    }
