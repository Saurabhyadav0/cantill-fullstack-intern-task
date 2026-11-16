"""Load CSV master data / PR batches / policy JSON into engine models.

Pure file IO + parsing (no web, no DB). Used by both the API seed and the tests.
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import date, datetime

from .models import Contract, Item, PoHistory, PRLine, Supplier
from .policy import Policy
from .core import MasterData


def _parse_dt(s: str) -> datetime:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"unparseable datetime: {s!r}")


def _parse_date(s: str):
    s = (s or "").strip()
    if not s:
        return None
    return _parse_dt(s).date()


def _num(s, default=None):
    s = (s or "").strip()
    if s == "":
        return default
    return float(s)


def _bool(s):
    return (s or "").strip().lower() in ("true", "1", "yes", "y")


# --------------------------------------------------------------------------- #
def load_items(path) -> list:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(Item(
                item_code=r["item_code"].strip(),
                description=r["description"].strip(),
                uom=r.get("uom", "").strip(),
                category=r.get("category", "").strip(),
                item_type=r.get("item_type", "").strip(),
                standard_price=_num(r.get("standard_price"), 0.0),
            ))
    return out


def load_suppliers(path) -> list:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cats = tuple(c.strip() for c in (r.get("categories", "") or "").split(";") if c.strip())
            out.append(Supplier(
                supplier_id=r["supplier_id"].strip(),
                name=r.get("name", "").strip(),
                city=r.get("city", "").strip(),
                categories=cats,
                status=r.get("status", "").strip(),
                on_time_pct=_num(r.get("on_time_pct"), 0.0),
                quality_rating=_num(r.get("quality_rating"), 0.0),
            ))
    return out


def load_po_history(path) -> list:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(PoHistory(
                po_number=r["po_number"].strip(),
                po_date=_parse_date(r["po_date"]),
                supplier_id=r["supplier_id"].strip(),
                item_code=r["item_code"].strip(),
                quantity=_num(r.get("quantity"), 0.0),
                uom=r.get("uom", "").strip(),
                unit_price=_num(r.get("unit_price"), 0.0),
                plant=r.get("plant", "").strip(),
                delivered_on_time=_bool(r.get("delivered_on_time")),
            ))
    return out


def load_contracts(register_path, lines_path, pdf_only_path=None) -> list:
    contracts = {}
    with open(register_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cid = r["contract_id"].strip()
            contracts[cid] = Contract(
                contract_id=cid,
                supplier_id=r["supplier_id"].strip(),
                supplier_name=r.get("supplier_name", "").strip(),
                start_date=_parse_date(r["start_date"]),
                end_date=_parse_date(r["end_date"]),
                value_cap=_num(r.get("value_cap"), 0.0),
                consumed_value=_num(r.get("consumed_value"), 0.0),
                source="register",
            )
    with open(lines_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cid = r["contract_id"].strip()
            if cid in contracts:
                contracts[cid].rates[r["item_code"].strip()] = _num(r.get("rate"), 0.0)

    if pdf_only_path and os.path.exists(pdf_only_path):
        with open(pdf_only_path, encoding="utf-8") as f:
            doc = json.load(f)
        for c in doc.get("contracts", []):
            cid = c["contract_id"]
            contract = Contract(
                contract_id=cid, supplier_id=c["supplier_id"],
                supplier_name=c.get("supplier_name", ""),
                start_date=_parse_date(c["start_date"]), end_date=_parse_date(c["end_date"]),
                value_cap=float(c["value_cap"]), consumed_value=float(c.get("consumed_value", 0)),
                source="pdf",
            )
            for ln in c.get("lines", []):
                contract.rates[ln["item_code"]] = float(ln["rate"])
            contracts[cid] = contract
    return list(contracts.values())


def load_pr_lines_from_rows(rows) -> list:
    out = []
    for r in rows:
        out.append(PRLine(
            pr_no=r["pr_no"].strip(),
            pr_line=int(float(r["pr_line"])),
            created_at=_parse_dt(r["created_at"]),
            requester=r.get("requester", "").strip(),
            department=r.get("department", "").strip(),
            plant=r.get("plant", "").strip(),
            item_code=(r.get("item_code", "") or "").strip(),
            description=(r.get("description", "") or "").strip(),
            quantity=_num(r.get("quantity"), 0.0),
            uom=r.get("uom", "").strip(),
            estimated_unit_price=_num(r.get("estimated_unit_price"), None),
            need_by_date=_parse_date(r.get("need_by_date")),
            urgency=(r.get("urgency", "") or "Normal").strip(),
        ))
    return out


def load_pr_lines(path) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        return load_pr_lines_from_rows(list(csv.DictReader(f)))


def load_pr_lines_from_csv_text(text: str) -> list:
    return load_pr_lines_from_rows(list(csv.DictReader(io.StringIO(text))))


def load_master_data(data_dir: str) -> MasterData:
    md = data_dir
    items = load_items(os.path.join(md, "master_data", "item_master.csv"))
    suppliers = load_suppliers(os.path.join(md, "master_data", "supplier_master.csv"))
    po_history = load_po_history(os.path.join(md, "master_data", "po_history.csv"))
    contracts = load_contracts(
        os.path.join(md, "contracts", "contract_register.csv"),
        os.path.join(md, "contracts", "contract_lines.csv"),
        os.path.join(md, "contracts", "pdf_only_contracts.json"),
    )
    plants = []
    ppath = os.path.join(md, "master_data", "plants.csv")
    if os.path.exists(ppath):
        with open(ppath, newline="", encoding="utf-8") as f:
            plants = [(r["plant"].strip(), r.get("name", "").strip()) for r in csv.DictReader(f)]
    return MasterData(items, suppliers, po_history, contracts, plants)


def load_policy(path: str) -> Policy:
    return Policy.from_file(path)
