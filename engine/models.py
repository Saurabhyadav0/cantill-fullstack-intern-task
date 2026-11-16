"""Plain data models for the decision engine.

The engine is intentionally pure: no web framework, no ORM, no database. It takes
dataclasses/dicts in and returns dataclasses/dicts out, so it is trivially testable
against the worked examples.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# --------------------------------------------------------------------------- #
# Master data
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Item:
    item_code: str
    description: str
    uom: str
    category: str
    item_type: str          # Material | Service | Capex
    standard_price: float


@dataclass(frozen=True)
class Supplier:
    supplier_id: str
    name: str
    city: str
    categories: tuple       # categories this supplier serves
    status: str             # Active | Inactive | Blocked
    on_time_pct: float
    quality_rating: float

    @property
    def is_active(self) -> bool:
        return self.status == "Active"


@dataclass(frozen=True)
class PoHistory:
    po_number: str
    po_date: date
    supplier_id: str
    item_code: str
    quantity: float
    uom: str
    unit_price: float
    plant: str
    delivered_on_time: bool


@dataclass
class Contract:
    contract_id: str
    supplier_id: str
    supplier_name: str
    start_date: date
    end_date: date
    value_cap: float
    consumed_value: float            # as at register's last update (or 0 for PDF-only)
    rates: dict = field(default_factory=dict)   # item_code -> rate
    source: str = "register"         # register | pdf

    def rate_for(self, item_code: str) -> Optional[float]:
        return self.rates.get(item_code)

    def covers(self, item_code: str) -> bool:
        return item_code in self.rates


# --------------------------------------------------------------------------- #
# Input: a raw PR line
# --------------------------------------------------------------------------- #
@dataclass
class PRLine:
    pr_no: str
    pr_line: int
    created_at: datetime
    requester: str
    department: str
    plant: str
    item_code: str                   # may be empty
    description: str
    quantity: float
    uom: str
    estimated_unit_price: Optional[float]
    need_by_date: Optional[date]
    urgency: str                     # Normal | Emergency

    # filled by the engine
    resolved_item_code: str = ""     # matched code or "NEW"
    match_confidence: float = 0.0
    match_note: str = ""


# --------------------------------------------------------------------------- #
# Working object: a clubbed requirement
# --------------------------------------------------------------------------- #
@dataclass
class Requirement:
    group_id: str
    lines: list                      # list[PRLine]
    resolved_item_code: str
    plant: str
    is_new_item: bool = False

    # computed
    requirement_date: date = None
    is_emergency: bool = False
    total_quantity: float = 0.0
    unit_price: float = 0.0          # full precision
    value: float = 0.0               # full precision (qty * unit_price)
    value_basis: str = ""            # which 3.1 clause gave the price

    # contract
    usable_contract: Optional[Contract] = None
    priced_contract_rate: Optional[float] = None

    # decision
    decision: str = ""               # PO | SOURCING_REQUEST
    route: str = ""
    policy_version: str = ""
    clause: str = ""
    reason: str = ""

    # supplier / price (for POs)
    supplier_id: Optional[str] = None
    po_unit_price: Optional[float] = None
    suggested_supplier_ids: list = field(default_factory=list)

    # consolidation
    po_id: Optional[str] = None

    @property
    def first_line(self) -> PRLine:
        return self.lines[0]


# --------------------------------------------------------------------------- #
# Output: one row per PR line (output schema, brief section 4)
# --------------------------------------------------------------------------- #
OUTPUT_COLUMNS = [
    "pr_no", "pr_line", "resolved_item_code", "group_id", "po_id",
    "decision", "route", "supplier_id", "unit_price", "group_value_inr",
    "suggested_supplier_ids", "policy_version", "reason",
]


@dataclass
class DecisionRow:
    pr_no: str
    pr_line: int
    resolved_item_code: str
    group_id: str
    po_id: str
    decision: str
    route: str
    supplier_id: str
    unit_price: str
    group_value_inr: str
    suggested_supplier_ids: str
    policy_version: str
    reason: str

    def as_dict(self) -> dict:
        return {c: getattr(self, c) for c in OUTPUT_COLUMNS}
