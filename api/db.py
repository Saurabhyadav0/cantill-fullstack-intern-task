"""SQLite persistence: versioned policies, audit log, added PDF-only contracts,
chat-created PR lines, and saved runs. Master data stays loaded from CSV (reference
data); the DB holds everything the app creates or versions.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(ROOT, "data"))
DB_PATH = os.environ.get("DB_PATH", os.path.join(ROOT, "api", "app.db"))
POLICY_V5 = os.environ.get("POLICY_V5", os.path.join(ROOT, "docs", "policy-v5.json"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS policies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version TEXT NOT NULL,
  effective_date TEXT NOT NULL,
  status TEXT NOT NULL,           -- draft | active | superseded
  body TEXT NOT NULL,             -- policy document JSON
  parent_version TEXT,
  summary TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, actor TEXT, action TEXT, entity TEXT, detail TEXT
);
CREATE TABLE IF NOT EXISTS added_contracts (
  contract_id TEXT PRIMARY KEY, body TEXT NOT NULL, created_at TEXT, created_by TEXT
);
CREATE TABLE IF NOT EXISTS pr_lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT, row TEXT NOT NULL, created_at TEXT, created_by TEXT
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, policy_version TEXT,
  label TEXT, rows TEXT, requirements TEXT
);
CREATE TABLE IF NOT EXISTS overrides (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT,
  group_id TEXT, field TEXT, old_value TEXT, new_value TEXT, reason TEXT
);
"""


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db(seed=True):
    con = connect()
    con.executescript(SCHEMA)
    con.commit()
    if seed:
        cur = con.execute("SELECT COUNT(*) AS n FROM policies")
        if cur.fetchone()["n"] == 0:
            with open(POLICY_V5, encoding="utf-8") as f:
                body = f.read()
            doc = json.loads(body)
            con.execute(
                "INSERT INTO policies(version,effective_date,status,body,summary,created_by,created_at)"
                " VALUES(?,?,?,?,?,?,?)",
                (str(doc.get("version", "5.0")), doc.get("effective_date", "2026-04-01"),
                 "active", body, "Seed policy v5.0", "system", datetime.utcnow().isoformat()),
            )
            con.commit()
            audit(con, "system", "seed", "policy", "seeded v5.0")
    con.close()


def audit(con, actor, action, entity, detail):
    con.execute("INSERT INTO audit(ts,actor,action,entity,detail) VALUES(?,?,?,?,?)",
                (datetime.utcnow().isoformat(), actor, action, entity, json.dumps(detail) if not isinstance(detail, str) else detail))
    con.commit()


# ---- policies ------------------------------------------------------------- #
def list_policies(con):
    return [dict(r) for r in con.execute(
        "SELECT id,version,effective_date,status,parent_version,summary,created_by,created_at"
        " FROM policies ORDER BY id DESC")]


def get_policy_row(con, pid):
    r = con.execute("SELECT * FROM policies WHERE id=?", (pid,)).fetchone()
    return dict(r) if r else None


def active_policy_doc(con, as_of: date = None):
    """Policy document active as of a date (default: the latest active)."""
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM policies WHERE status IN ('active','superseded') ORDER BY effective_date DESC, id DESC")]
    if as_of:
        rows = [r for r in rows if r["effective_date"] <= as_of.isoformat()]
    for r in rows:
        return json.loads(r["body"])
    # fallback to file
    with open(POLICY_V5, encoding="utf-8") as f:
        return json.load(f)


def insert_policy(con, doc, status, summary, parent_version, actor):
    body = json.dumps(doc, indent=2)
    con.execute(
        "INSERT INTO policies(version,effective_date,status,body,parent_version,summary,created_by,created_at)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (str(doc.get("version")), doc.get("effective_date"), status, body,
         parent_version, summary, actor, datetime.utcnow().isoformat()))
    con.commit()
    return con.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def approve_policy(con, pid, actor):
    row = get_policy_row(con, pid)
    if not row:
        return None
    # supersede current actives with effective_date <= this one
    con.execute("UPDATE policies SET status='superseded' WHERE status='active' AND effective_date<=?",
                (row["effective_date"],))
    con.execute("UPDATE policies SET status='active' WHERE id=?", (pid,))
    con.commit()
    audit(con, actor, "approve", "policy", f"activated policy #{pid} v{row['version']}")
    return get_policy_row(con, pid)


# ---- added contracts ------------------------------------------------------ #
def add_contract(con, body: dict, actor):
    con.execute("INSERT OR REPLACE INTO added_contracts(contract_id,body,created_at,created_by) VALUES(?,?,?,?)",
                (body["contract_id"], json.dumps(body), datetime.utcnow().isoformat(), actor))
    con.commit()
    audit(con, actor, "add", "contract", body["contract_id"])


def list_added_contracts(con):
    return [json.loads(r["body"]) for r in con.execute("SELECT body FROM added_contracts")]
