"""API tests: list, fetch, decide; and that nothing changes without a named human decision."""
import pytest
from fastapi.testclient import TestClient

import db
from agent.generate_drafts import draft_and_store
from api.main import app


@pytest.fixture
def client(conn, tmp_path, monkeypatch):
    draft_and_store(conn, "A000001")
    monkeypatch.setenv("FRAUDFLOW_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("FRAUDFLOW_API_KEY", "secret")
    return TestClient(app, headers={"X-API-Key": "secret"})


def test_key_required(client):
    assert TestClient(app).get("/cases").status_code == 401


def test_list_and_fetch_case(client):
    cases = client.get("/cases").json()
    assert [c["case_id"] for c in cases] == ["C-A000001"]
    assert "LOW CONFIDENCE" in cases[0]["label"] or "Checks passed" in cases[0]["label"]
    full = client.get("/cases/C-A000001").json()
    assert full["facts"]["flagged_transaction"]["tx_id"] == "T0000002"
    assert client.get("/alerts", params={"status": "drafted"}).json()[0]["alert_id"] == "A000001"


def test_decision_is_logged_once(client):
    res = client.post("/cases/C-A000001/decision", json={"decision": "approve", "reviewer": "Test Reviewer"})
    assert res.status_code == 200 and res.json()["status"] == "approved"
    log = client.get("/decisions").json()
    assert log[0]["reviewer"] == "Test Reviewer" and log[0]["decided_at"]
    again = client.post("/cases/C-A000001/decision", json={"decision": "reject", "reviewer": "Someone"})
    assert again.status_code == 409
    assert client.get("/cases").json() == []


def test_edit_needs_text_and_reviewer_needs_name(client):
    assert client.post("/cases/C-A000001/decision", json={"decision": "edit", "reviewer": "Ann"}).status_code == 422
    assert client.post("/cases/C-A000001/decision", json={"decision": "approve", "reviewer": ""}).status_code == 422
    assert client.post("/cases/C-A000001/decision", json={"decision": "file_report", "reviewer": "Ann"}).status_code == 422


def test_review_page_is_labelled_fallback(client):
    html = client.get("/review").text
    assert "FALLBACK APPROVAL PAGE" in html and "not Power Automate" in html


def test_read_only_demo_refuses_decisions(client, monkeypatch):
    monkeypatch.setenv("FRAUDFLOW_READ_ONLY", "1")
    res = client.post("/cases/C-A000001/decision", json={"decision": "approve", "reviewer": "Visitor"})
    assert res.status_code == 403
    assert client.get("/config").json() == {"read_only": True}
    assert client.get("/cases").json()[0]["status"] == "pending_review"
