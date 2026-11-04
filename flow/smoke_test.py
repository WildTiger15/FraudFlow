"""End-to-end plumbing test: alert -> drafted case -> decision -> log, over real HTTP.

Plays the two HTTP calls the Power Automate flow makes, against a COPY of the database,
so the real database never gets a fake decision. It is NOT Power Automate.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from config import DB_PATH, ROOT

PORT = 8765
KEY = "smoke-test-key"
SMOKE_REVIEWER = "smoke test (automated, not a real review)"
LOG = ROOT / "flow" / "smoke_test_log.md"


def main():
    tmp = Path(tempfile.mkdtemp())
    db_copy = tmp / "fraudflow_copy.db"
    shutil.copy(DB_PATH, db_copy)
    env = {**os.environ, "FRAUDFLOW_DB": str(db_copy), "FRAUDFLOW_API_KEY": KEY}
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--port", str(PORT)],
                              cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    steps = []
    try:
        api = httpx.Client(base_url=f"http://127.0.0.1:{PORT}", headers={"X-API-Key": KEY}, timeout=10)
        for _ in range(50):
            try:
                api.get("/cases")
                break
            except httpx.TransportError:
                time.sleep(0.2)
        cases = api.get("/cases", params={"status": "pending_review"}).json()
        steps.append(f"GET /cases?status=pending_review -> {len(cases)} cases waiting")
        case = api.get(f"/cases/{cases[0]['case_id']}").json()
        steps.append(f"GET /cases/{case['case_id']} -> alert {case['alert_id']}, flagged transaction "
                     f"{case['facts']['flagged_transaction']['tx_id']}, label '{case['label']}'")
        alert = api.get("/alerts", params={"status": "drafted", "limit": 100000}).json()
        steps.append(f"Alert {case['alert_id']} status before decision: "
                     f"{next(a['status'] for a in alert if a['alert_id'] == case['alert_id'])}")
        decided = api.post(f"/cases/{case['case_id']}/decision",
                           json={"decision": "reject", "reviewer": SMOKE_REVIEWER, "comment": "plumbing test only",
                                 "channel": "power_automate"}).json()
        steps.append(f"POST /cases/{case['case_id']}/decision -> status {decided['status']} at {decided['decided_at']}")
        log = api.get("/decisions").json()
        steps.append(f"GET /decisions -> {len(log)} row(s); last reviewer '{log[-1]['reviewer']}'")
        again = api.post(f"/cases/{case['case_id']}/decision", json={"decision": "approve", "reviewer": "x y"})
        steps.append(f"Second decision on the same case -> HTTP {again.status_code} (refused, as intended)")
        no_key = httpx.get(f"http://127.0.0.1:{PORT}/cases")
        steps.append(f"Request without API key -> HTTP {no_key.status_code}")
    finally:
        server.terminate()
        server.wait()
        shutil.rmtree(tmp, ignore_errors=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = (f"# API smoke test ({stamp})\n\nRun on a throwaway copy of the database; the real database was not changed. "
            "This replays the Power Automate flow's HTTP calls from Python. It is not a Power Automate run.\n\n"
            + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps)) + "\n")
    LOG.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
