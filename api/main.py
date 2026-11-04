"""Small API that the Power Automate flow (or the fallback review page) calls.

Run: uvicorn api.main:app --port 8000
Endpoints:
  GET  /alerts?status=new           list alerts
  GET  /cases?status=pending_review list drafted cases waiting for a person
  GET  /cases/{case_id}             full draft, facts and check results
  POST /cases/{case_id}/decision    record approve / edit / reject by a named reviewer
  GET  /decisions                   the decision log (audit trail)
  GET  /review                      FALLBACK approval page (not Power Automate)
The API never approves, closes or files anything by itself: only a POSTed human decision changes a case.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import db

app = FastAPI(title="FraudFlow API", description="Synthetic data only. Every case needs a human decision.")
REVIEW_PAGE = Path(__file__).parent / "review_page.html"


def get_conn():
    conn = db.connect(os.environ.get("FRAUDFLOW_DB"))
    try:
        yield conn
    finally:
        conn.close()


def require_key(x_api_key: Optional[str] = Header(default=None)):
    """If FRAUDFLOW_API_KEY is set, callers (the flow) must send it in the X-API-Key header."""
    expected = os.environ.get("FRAUDFLOW_API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Missing or wrong X-API-Key")


class Decision(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    reviewer: str = Field(min_length=2, description="Name of the person deciding")
    comment: Optional[str] = None
    edited_summary: Optional[str] = Field(default=None, description="Required when decision is 'edit'")
    review_seconds: Optional[float] = Field(default=None, ge=0)
    channel: Literal["power_automate", "fallback_page"] = "power_automate"


def case_row_to_dict(row, full=False):
    case = {
        "case_id": row["case_id"], "alert_id": row["alert_id"], "status": row["status"],
        "confidence": row["confidence"], "drafted_by": row["drafted_by"],
        "check_passed": bool(row["check_passed"]), "check_failures": json.loads(row["check_failures"]),
        "created_at": row["created_at"],
    }
    draft = json.loads(row["draft_json"])
    case["summary"] = draft["summary"]
    case["label"] = ("LOW CONFIDENCE - check every fact" if row["confidence"] == "low" else "Checks passed") + \
        (" - drafted WITHOUT AI (template)" if row["drafted_by"] == "template_no_ai" else "")
    if full:
        case["draft"] = draft
        case["facts"] = json.loads(row["facts_json"])
    return case


@app.get("/alerts", dependencies=[Depends(require_key)])
def list_alerts(status: str = "new", limit: int = 50, conn=Depends(get_conn)):
    rows = conn.execute("SELECT * FROM alerts WHERE status = ? ORDER BY step, alert_id LIMIT ?",
                        (status, limit)).fetchall()
    return [dict(r) for r in rows]


@app.get("/cases", dependencies=[Depends(require_key)])
def list_cases(status: str = "pending_review", limit: int = 50, conn=Depends(get_conn)):
    rows = conn.execute("SELECT * FROM cases WHERE status = ? ORDER BY case_id LIMIT ?", (status, limit)).fetchall()
    return [case_row_to_dict(r) for r in rows]


@app.get("/cases/{case_id}", dependencies=[Depends(require_key)])
def get_case(case_id: str, conn=Depends(get_conn)):
    row = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case_row_to_dict(row, full=True)


@app.post("/cases/{case_id}/decision", dependencies=[Depends(require_key)])
def record_decision(case_id: str, body: Decision, conn=Depends(get_conn)):
    row = conn.execute("SELECT status FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if row["status"] != "pending_review":
        raise HTTPException(status_code=409, detail="Case already decided")
    if body.decision == "edit" and not (body.edited_summary or "").strip():
        raise HTTPException(status_code=422, detail="An 'edit' decision needs edited_summary")
    decided_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO decisions (case_id, decision, reviewer, comment, edited_summary, review_seconds, channel,
           decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (case_id, body.decision, body.reviewer.strip(), body.comment, body.edited_summary, body.review_seconds,
         body.channel, decided_at))
    new_status = "rejected" if body.decision == "reject" else "approved"
    conn.execute("UPDATE cases SET status = ? WHERE case_id = ?", (new_status, case_id))
    conn.execute("UPDATE alerts SET status = 'decided' WHERE alert_id = (SELECT alert_id FROM cases WHERE case_id = ?)",
                 (case_id,))
    conn.commit()
    return {"case_id": case_id, "status": new_status, "decision": body.decision, "reviewer": body.reviewer.strip(),
            "decided_at": decided_at,
            "note": "Recorded only. FraudFlow does not file or send any report; that stays with the AML team."}


@app.get("/decisions", dependencies=[Depends(require_key)])
def list_decisions(conn=Depends(get_conn)):
    return [dict(r) for r in conn.execute("SELECT * FROM decisions ORDER BY decision_id").fetchall()]


@app.get("/review", response_class=HTMLResponse)
def review_page():
    """Fallback approval page for when Power Automate is not available. Clearly labelled as such."""
    return REVIEW_PAGE.read_text(encoding="utf-8")
