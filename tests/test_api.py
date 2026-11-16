"""API / integration tests via FastAPI TestClient, including the blind-test loop
(process -> amend -> approve -> reprocess) proving policy-as-data changes decisions
with no code change.
"""
import os
import tempfile

import pytest
from conftest import requires_data, DATA, POLICY


@pytest.fixture()
def client(monkeypatch):
    # isolated temp DB per test module
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("DB_PATH", tmp.name)
    monkeypatch.setenv("DATA_DIR", DATA)
    monkeypatch.setenv("POLICY_V5", POLICY)
    # import after env is set so db module picks up paths
    import importlib
    import api.db as dbmod
    importlib.reload(dbmod)
    import api.main as mainmod
    importlib.reload(mainmod)
    from fastapi.testclient import TestClient
    with TestClient(mainmod.app) as c:
        yield c
    os.unlink(tmp.name)


@requires_data
def test_process_batch_and_counts(client):
    r = client.post("/api/process-batch", data={"source": "sample", "label": "run1"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 186
    assert body["policy_version"] == "5.0"
    # a known worked example comes back correctly through the API
    row = next(x for x in body["rows"] if x["pr_no"] == "PR-26-00019")
    assert row["route"] == "CONTRACT_PO" and row["supplier_id"] == "S001"


@requires_data
def test_chat_parse_matches_item(client):
    r = client.post("/api/chat/parse", json={"text": "need 200 nitrile gloves for Chakan by next Friday"})
    body = r.json()
    assert body["interpretation"]["resolved_item_code"] == "ITM-1048"
    assert body["interpretation"]["plant"] == "CHK1"
    assert body["interpretation"]["quantity"] == 200


@requires_data
def test_no_blocked_supplier_in_output(client):
    body = client.post("/api/process-batch", data={"source": "sample"}).json()
    sup = client.get("/api/suppliers").json()
    banned = {s["supplier_id"] for s in sup if s["status"] in ("Blocked", "Inactive")}
    for row in body["rows"]:
        assert row["supplier_id"] not in banned


@requires_data
def test_amendment_changes_a_decision(client):
    """Blind-test shape: Run1 then amend+approve then Run2, decision must change."""
    run1 = client.post("/api/process-batch", data={"source": "sample", "label": "run1"}).json()
    r1 = next(x for x in run1["rows"] if x["pr_no"] == "PR-26-00001")
    assert r1["route"] == "RFQ"            # value ~2.59L, above spot limit

    draft = client.post("/api/policies/amendment", json={
        "text": "Raise the Spot PO limit to 3,00,000", "effective_date": "2026-04-01"}).json()
    assert draft["changes"]
    appr = client.post(f"/api/policies/{draft['draft_id']}/approve", json={}).json()
    assert appr["active_version"] == "5.1"

    run2 = client.post("/api/process-batch", data={"source": "sample", "label": "run2"}).json()
    assert run2["policy_version"] == "5.1"
    r2 = next(x for x in run2["rows"] if x["pr_no"] == "PR-26-00001")
    assert r2["route"] == "SPOT_PO"        # flipped with no code change


@requires_data
def test_add_rule_new_kind_plant_specific(client):
    """A brand-new *kind* of rule (plant-specific) can be added as data."""
    client.post("/api/process-batch", data={"source": "sample"})
    ops = [{"op": "add_rule", "before": "5.3", "rule": {
        "id": "amend-chk1", "clause": "amend-chk1", "name": "CHK1 small emergency fast PO",
        "when": {"all": [
            {"field": "requirement.plant", "op": "eq", "value": "CHK1"},
            {"field": "requirement.is_emergency", "op": "eq", "value": True},
            {"field": "requirement.value", "op": "lte", "value": 100000}]},
        "outcome": {"decision": "PO", "route": "EMERGENCY_PO", "supplier_strategy": "first_preferred",
                    "price": "reference_price"}}}]
    draft = client.post("/api/policies/amendment", json={"ops": ops}).json()
    assert any("Add a new rule" in c for c in draft["changes"])
    appr = client.post(f"/api/policies/{draft['draft_id']}/approve", json={}).json()
    assert appr["active_version"]
    # reprocessing uses the new rule without any code change
    run = client.post("/api/process-batch", data={"source": "sample"}).json()
    assert run["policy_version"] == appr["active_version"]


@requires_data
def test_preferred_export(client):
    r = client.get("/api/export/preferred.csv", params={"as_of": "2026-11-01"})
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0] == "item_code,rank,supplier_id,reference_price"
    # ITM-1048 rank 1 is S029 (from worked example)
    r1 = [l for l in lines if l.startswith("ITM-1048,1,")]
    assert r1 and r1[0].split(",")[2] == "S029"
