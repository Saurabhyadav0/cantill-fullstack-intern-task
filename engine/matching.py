"""Item matching (policy section 1).

Resolve a PR line to an item master code. If an item_code is given and valid, use it.
Otherwise match the free-text description. Requesters use short forms
("brg 6205 2rs" -> Ball bearing 6205-2RS), so we normalise + score and only accept a
match above a confidence threshold; below it the line is a NEW item (never invented).

Pure stdlib (difflib) so it has no binary dependencies.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

NEW = "NEW"

# Common requester abbreviations -> canonical token(s).
_ABBREV = {
    "brg": "bearing", "brgs": "bearing", "bearings": "bearing",
    "hyd": "hydraulic", "hydr": "hydraulic",
    "pneu": "pneumatic",
    "ss": "ss", "ms": "ms",
    "sol": "solenoid", "solnd": "solenoid",
    "cyl": "cylinder",
    "elec": "electrical",
    "gkt": "gasket",
    "wshr": "washer", "wshers": "washer",
    "blt": "bolt", "blts": "bolt",
    "sheet": "sheet", "plt": "plate",
    "calib": "calibration", "cal": "calibration",
    "svc": "service", "srvc": "service",
    "mtr": "meter",
    "gr": "gr",
    "vci": "vci",
    "eot": "eot",
}

_STOP = {"for", "the", "a", "an", "of", "and", "to", "with", "qty", "nos", "no",
         "pcs", "pc", "set", "maintenance", "mtce", "urgent", "please", "pls",
         "approx", "approximately", "spare", "spares", "new", "inch", "mm"}


def normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = text.replace("×", "x")
    # collapse dimension 'x' between digits so "600x900" ~ "600900", "50x100" ~ "50100"
    text = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "", text)
    # non-alphanumerics -> space
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(text: str) -> list:
    toks = []
    for t in normalize(text).split():
        t = _ABBREV.get(t, t)
        toks.append(t)
    return toks


def _content_tokens(text: str) -> set:
    return {t for t in _tokens(text) if t not in _STOP}


def _digit_tokens(text: str) -> set:
    return {t for t in _tokens(text) if any(c.isdigit() for c in t)}


def _score(query: str, candidate: str) -> float:
    """Combined similarity in [0, 1]."""
    nq, nc = " ".join(_tokens(query)), " ".join(_tokens(candidate))
    if not nq or not nc:
        return 0.0
    seq = SequenceMatcher(None, nq.replace(" ", ""), nc.replace(" ", "")).ratio()
    qset, cset = _content_tokens(query), _content_tokens(candidate)
    jac = len(qset & cset) / len(qset | cset) if (qset | cset) else 0.0
    # digit/model-number agreement is a strong signal (6308, 6205, 600900 ...)
    qd, cd = _digit_tokens(query), _digit_tokens(candidate)
    if qd:
        dmatch = len(qd & cd) / len(qd)
    else:
        dmatch = 1.0 if not cd else 0.5
    return 0.45 * seq + 0.35 * jac + 0.20 * dmatch


ACCEPT_THRESHOLD = 0.55     # below -> NEW item
AMBIGUOUS_MARGIN = 0.06     # if top two are within this, flag as ambiguous


def match_item(item_code: str, description: str, items_by_code: dict, items: list):
    """Return (resolved_code, confidence, note).

    items_by_code: {code: Item}; items: list[Item].
    """
    code = (item_code or "").strip()
    if code and code in items_by_code:
        return code, 1.0, "exact item_code"

    if not (description or "").strip():
        return NEW, 0.0, "no item_code and no description"

    scored = sorted(
        ((it, _score(description, it.description)) for it in items),
        key=lambda x: x[1], reverse=True,
    )
    best, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0

    if best_score < ACCEPT_THRESHOLD:
        return NEW, best_score, f"no confident match (best {best.item_code} {best_score:.2f}) -> new item"

    note = f"matched '{description}' -> {best.item_code} ({best.description}) [{best_score:.2f}]"
    if best_score - second_score < AMBIGUOUS_MARGIN:
        note += f"; close to {scored[1][0].item_code} [{second_score:.2f}] - review"
    return best.item_code, best_score, note
