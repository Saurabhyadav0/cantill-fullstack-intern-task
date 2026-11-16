"""FastAPI app: chat intake, batch processing, buyer workspace, policy versioning +
amendments, contracts, exports. The decision engine (pure) does the thinking; this
layer handles IO, persistence and the UI.
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import date, datetime

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from engine.core import MasterData, PreferredEngine, process_batch
from engine.loaders import (load_master_data, load_pr_lines_from_csv_text,
                            load_pr_lines_from_rows)
from engine.models import OUTPUT_COLUMNS, Contract
from engine.policy import Policy

from . import amend, chat, db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(ROOT, "web")

app = FastAPI(title="Corvo PR->PO", version="1.0")

_BASE_MD: MasterData = None            # master data from CSV (reference)
_LAST_RUN = {"rows": [], "requirements": [], "label": None, "policy_version": None}


# --------------------------------------------------------------------------- #
def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def _master_data(con) -> MasterData:
    """Base CSV master data + any contracts added at runtime (PDF-only)."""
    base = _BASE_MD
    added = db.list_added_contracts(con)
    if not added:
        return base
    contracts = list(base.contracts)
    have = {c.contract_id for c in contracts}
    for c in added:
        if c["contract_id"] in have:
            contracts = [x for x in contracts if x.contract_id != c["contract_id"]]
        contract = Contract(
            contract_id=c["contract_id"], supplier_id=c["supplier_id"],
            supplier_name=c.get("supplier_name", ""),
            start_date=_parse_date(c["start_date"]), end_date=_parse_date(c["end_date"]),
            value_cap=float(c["value_cap"]), consumed_value=float(c.get("consumed_value", 0)),
            source="pdf")
        for ln in c.get("lines", []):
            contract.rates[ln["item_code"]] = float(ln["rate"])
        contracts.append(contract)
    return MasterData(base.items, base.suppliers, base.po_history, contracts, base.plants)


def _active_policy(con, as_of=None) -> Policy:
    return Policy(db.active_policy_doc(con, as_of))


@app.on_event("startup")
def _startup():
    global _BASE_MD
    db.init_db(seed=True)
    try:
        _BASE_MD = load_master_data(db.DATA_DIR)
    except Exception as exc:   # hosting without data present: boot anyway, show a banner
        print(f"[startup] master data not loaded from {db.DATA_DIR}: {exc}")
        _BASE_MD = MasterData([], [], [], [], [])


# --------------------------------------------------------------------------- #
# Meta / lookups
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/meta")
def meta():
    con = db.connect()
    md = _master_data(con)
    pol = _active_policy(con)
    con.close()
    return {
        "plants": [{"plant": p, "name": n} for p, n in md.plants],
        "counts": {"items": len(md.items), "suppliers": len(md.suppliers),
                   "contracts": len(md.contracts), "po_history": len(md.po_history)},
        "active_policy": {"version": pol.version, "effective_date": pol.effective_date},
    }


@app.get("/api/items")
def items(q: str = "", limit: int = 20):
    md = _BASE_MD
    q = q.lower().strip()
    out = [it for it in md.items if not q or q in it.description.lower() or q in it.item_code.lower()]
    return [{"item_code": it.item_code, "description": it.description, "uom": it.uom,
             "category": it.category, "item_type": it.item_type,
             "standard_price": it.standard_price} for it in out[:limit]]


@app.get("/api/suppliers")
def suppliers():
    return [{"supplier_id": s.supplier_id, "name": s.name, "city": s.city,
             "categories": list(s.categories), "status": s.status,
             "on_time_pct": s.on_time_pct, "quality_rating": s.quality_rating}
            for s in _BASE_MD.suppliers]


@app.get("/api/contracts")
def contracts():
    con = db.connect()
    md = _master_data(con)
    con.close()
    return [{"contract_id": c.contract_id, "supplier_id": c.supplier_id,
             "supplier_name": c.supplier_name, "start_date": c.start_date.isoformat(),
             "end_date": c.end_date.isoformat(), "value_cap": c.value_cap,
             "consumed_value": c.consumed_value, "source": c.source,
             "items": [{"item_code": k, "rate": v} for k, v in c.rates.items()]}
            for c in md.contracts]


@app.post("/api/contracts")
async def add_contract(request: Request):
    body = await request.json()
    actor = body.pop("actor", "procurement")
    required = ["contract_id", "supplier_id", "start_date", "end_date", "value_cap", "lines"]
    for k in required:
        if k not in body:
            raise HTTPException(400, f"missing field: {k}")
    con = db.connect()
    db.add_contract(con, body, actor)
    con.close()
    return {"ok": True, "contract_id": body["contract_id"]}


# --------------------------------------------------------------------------- #
# Chat intake
# --------------------------------------------------------------------------- #
@app.post("/api/chat/parse")
async def chat_parse(request: Request):
    body = await request.json()
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(400, "empty text")
    con = db.connect()
    md = _master_data(con)
    con.close()
    return chat.parse(text, md)


@app.get("/api/prs")
def list_prs():
    con = db.connect()
    rows = [json.loads(r["row"]) for r in con.execute("SELECT row FROM pr_lines ORDER BY id")]
    con.close()
    return rows


@app.post("/api/prs")
async def create_pr(request: Request):
    body = await request.json()
    actor = body.get("actor", "requester")
    con = db.connect()
    n = con.execute("SELECT COUNT(*) AS n FROM pr_lines").fetchone()["n"]
    pr_no = body.get("pr_no") or f"PR-NEW-{n+1:05d}"
    row = {
        "pr_no": pr_no, "pr_line": body.get("pr_line", 1),
        "created_at": body.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "requester": actor, "department": body.get("department", ""),
        "plant": body.get("plant", ""), "item_code": body.get("item_code", ""),
        "description": body.get("description", ""), "quantity": body.get("quantity", 0),
        "uom": body.get("uom", "NOS"),
        "estimated_unit_price": body.get("estimated_unit_price", ""),
        "need_by_date": body.get("need_by_date", ""), "urgency": body.get("urgency", "Normal"),
    }
    con.execute("INSERT INTO pr_lines(row,created_at,created_by) VALUES(?,?,?)",
                (json.dumps(row), datetime.utcnow().isoformat(), actor))
    con.commit()
    db.audit(con, actor, "create", "pr_line", pr_no)
    con.close()
    return {"ok": True, "pr": row}


# --------------------------------------------------------------------------- #
# Batch processing + exports
# --------------------------------------------------------------------------- #
def _run(con, lines, label, as_of=None):
    md = _master_data(con)
    pol = _active_policy(con, as_of)
    rows, reqs = process_batch(md, pol, lines)
    row_dicts = [r.as_dict() for r in rows]
    req_view = _requirements_view(reqs, md)
    con.execute("INSERT INTO runs(created_at,policy_version,label,rows,requirements) VALUES(?,?,?,?,?)",
                (datetime.utcnow().isoformat(), pol.version, label,
                 json.dumps(row_dicts), json.dumps(req_view)))
    con.commit()
    db.audit(con, "system", "process", "batch", {"label": label, "lines": len(lines), "policy": pol.version})
    _LAST_RUN.update(rows=row_dicts, requirements=req_view, label=label, policy_version=pol.version)
    return {"policy_version": pol.version, "label": label, "count": len(row_dicts),
            "rows": row_dicts, "requirements": req_view}


def _requirements_view(reqs, md):
    out = []
    for r in sorted(reqs, key=lambda x: x.group_id):
        item = md.items_by_code.get(r.resolved_item_code)
        out.append({
            "group_id": r.group_id, "po_id": r.po_id or "",
            "resolved_item_code": r.resolved_item_code,
            "item_description": item.description if item else (r.first_line.description),
            "plant": r.plant, "requirement_date": r.requirement_date.isoformat() if r.requirement_date else "",
            "is_emergency": r.is_emergency, "total_quantity": r.total_quantity,
            "unit_price": r.unit_price, "value": round(r.value, 2), "value_basis": r.value_basis,
            "decision": r.decision, "route": r.route, "clause": r.clause,
            "policy_version": r.policy_version, "reason": r.reason,
            "supplier_id": r.supplier_id or "",
            "po_unit_price": r.po_unit_price,
            "suggested_supplier_ids": r.suggested_supplier_ids,
            "lines": [{"pr_no": l.pr_no, "pr_line": l.pr_line, "description": l.description,
                       "quantity": l.quantity, "need_by_date": l.need_by_date.isoformat() if l.need_by_date else "",
                       "urgency": l.urgency, "created_at": l.created_at.isoformat(),
                       "match_note": l.match_note} for l in r.lines],
            "status": "pending", "override": None,
        })
    return out


@app.post("/api/process-batch")
async def process_batch_ep(file: UploadFile = File(None), source: str = Form(None),
                           label: str = Form("run"), as_of: str = Form(None)):
    con = db.connect()
    if file is not None:
        text = (await file.read()).decode("utf-8")
        lines = load_pr_lines_from_csv_text(text)
    elif source == "sample":
        from engine.loaders import load_pr_lines
        lines = load_pr_lines(os.path.join(db.DATA_DIR, "pr_batches", "sample_pr_batch.csv"))
    elif source == "stored":
        rows = [json.loads(r["row"]) for r in con.execute("SELECT row FROM pr_lines ORDER BY id")]
        lines = load_pr_lines_from_rows(rows)
    else:
        con.close()
        raise HTTPException(400, "provide a file or source=sample|stored")
    out = _run(con, lines, label, _parse_date(as_of))
    con.close()
    return out


@app.get("/api/export/decisions.csv")
def export_decisions():
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=OUTPUT_COLUMNS)
    w.writeheader()
    for row in _LAST_RUN["rows"]:
        w.writerow(row)
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=decisions.csv"})


@app.get("/api/export/preferred.csv")
def export_preferred(as_of: str = None, top: int = 3):
    con = db.connect()
    md = _master_data(con)
    pol = _active_policy(con)
    con.close()
    d = _parse_date(as_of) or date.today()
    pe = PreferredEngine(md, pol)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["item_code", "rank", "supplier_id", "reference_price"])
    for it in md.items:
        ranked = pe.ranked_list(it.item_code, d)[:top]
        for rank, (s, _score, ref) in enumerate(ranked, start=1):
            w.writerow([it.item_code, rank, s.supplier_id,
                        "" if ref is None else round(ref, 2)])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=preferred.csv"})


@app.get("/api/requirements")
def requirements():
    return _LAST_RUN["requirements"]


@app.post("/api/requirements/{group_id}/approve")
async def approve_req(group_id: str, request: Request):
    body = await request.json()
    actor = body.get("actor", "buyer")
    for r in _LAST_RUN["requirements"]:
        if r["group_id"] == group_id:
            r["status"] = "approved"
            con = db.connect()
            db.audit(con, actor, "approve", "requirement",
                     {"group_id": group_id, "route": r["route"], "po_id": r["po_id"]})
            con.close()
            return {"ok": True, "requirement": r}
    raise HTTPException(404, "requirement not found")


@app.post("/api/requirements/{group_id}/override")
async def override_req(group_id: str, request: Request):
    body = await request.json()
    actor = body.get("actor", "buyer")
    reason = (body.get("reason") or "").strip()
    if not reason:
        raise HTTPException(400, "override requires a reason")
    field, value = body.get("field", ""), body.get("value", "")
    for r in _LAST_RUN["requirements"]:
        if r["group_id"] == group_id:
            old = r.get(field)
            r[field] = value
            r["status"] = "overridden"
            r["override"] = {"by": actor, "field": field, "from": old, "to": value, "reason": reason}
            con = db.connect()
            con.execute("INSERT INTO overrides(ts,actor,group_id,field,old_value,new_value,reason)"
                        " VALUES(?,?,?,?,?,?,?)",
                        (datetime.utcnow().isoformat(), actor, group_id, field, str(old), str(value), reason))
            con.commit()
            db.audit(con, actor, "override", "requirement",
                     {"group_id": group_id, "field": field, "reason": reason})
            con.close()
            return {"ok": True, "requirement": r}
    raise HTTPException(404, "requirement not found")


# --------------------------------------------------------------------------- #
# Policies + amendments
# --------------------------------------------------------------------------- #
@app.get("/api/policies")
def policies():
    con = db.connect()
    out = db.list_policies(con)
    con.close()
    return out


@app.get("/api/policies/{pid}")
def policy_detail(pid: int):
    con = db.connect()
    row = db.get_policy_row(con, pid)
    con.close()
    if not row:
        raise HTTPException(404, "not found")
    row["body"] = json.loads(row["body"])
    return row


@app.post("/api/policies/amendment")
async def amendment(request: Request):
    """Create a DRAFT new version from a description/ops. Returns a plain-language preview."""
    body = await request.json()
    actor = body.get("actor", "procurement")
    con = db.connect()
    current = db.active_policy_doc(con)
    ops = body.get("ops")
    used_llm = False
    if not ops:
        text = body.get("text", "")
        if not text.strip():
            con.close()
            raise HTTPException(400, "provide ops or text")
        ops, used_llm = amend.parse_with_llm(text, current)
    if not ops:
        con.close()
        raise HTTPException(422, "could not derive any changes from the description; try structured ops")

    # bump version + effective date
    new_doc = amend.apply_ops(current, ops)
    if not any(o.get("op") == "set_meta" and "version" in o.get("values", {}) for o in ops):
        try:
            new_doc["version"] = f"{float(current.get('version', '5.0')) + 0.1:.1f}"
        except ValueError:
            new_doc["version"] = str(current.get("version", "5.0")) + "+amend"
    if body.get("effective_date"):
        new_doc["effective_date"] = body["effective_date"]

    summary = amend.summarise(current, ops)
    pid = db.insert_policy(con, new_doc, "draft",
                           " ".join(summary)[:500], str(current.get("version")), actor)
    db.audit(con, actor, "draft", "policy", {"id": pid, "ops": ops})
    con.close()
    return {"draft_id": pid, "new_version": new_doc.get("version"),
            "effective_date": new_doc.get("effective_date"),
            "changes": summary, "ops": ops, "used_llm": used_llm}


@app.post("/api/policies/{pid}/approve")
async def approve_policy_ep(pid: int, request: Request):
    body = await request.json()
    actor = body.get("actor", "procurement")
    con = db.connect()
    row = db.approve_policy(con, pid, actor)
    con.close()
    if not row:
        raise HTTPException(404, "not found")
    return {"ok": True, "active_version": row["version"], "effective_date": row["effective_date"]}


@app.get("/api/audit")
def audit_log(limit: int = 100):
    con = db.connect()
    rows = [dict(r) for r in con.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))]
    con.close()
    return rows


# --------------------------------------------------------------------------- #
# Frontend
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
