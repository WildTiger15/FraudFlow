"""Build a small read-only demo database for the public showcase (Render).

Copies only: the drafted cases, their alerts, the first 500 other alerts, and the detection metrics.
All synthetic PaySim data. No decisions are copied, and the demo API refuses new ones.
"""
import sqlite3

from config import ROOT
from db import connect

DEMO_DB = ROOT / "data" / "demo" / "fraudflow_demo.db"


def main():
    DEMO_DB.parent.mkdir(parents=True, exist_ok=True)
    DEMO_DB.unlink(missing_ok=True)
    demo = connect(DEMO_DB)
    demo.close()
    src = connect()
    src.execute("ATTACH DATABASE ? AS demo", (str(DEMO_DB),))
    src.execute("INSERT INTO demo.cases SELECT * FROM cases")
    src.execute("""INSERT INTO demo.alerts SELECT * FROM alerts WHERE alert_id IN (SELECT alert_id FROM cases)
                   OR alert_id IN (SELECT alert_id FROM alerts WHERE status = 'new' ORDER BY alert_id LIMIT 500)""")
    src.execute("CREATE TABLE demo.detection_metrics AS SELECT * FROM detection_metrics")
    src.commit()
    src.execute("DETACH DATABASE demo")
    with sqlite3.connect(DEMO_DB) as check:
        counts = {t: check.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("cases", "alerts", "decisions", "detection_metrics")}
        check.execute("VACUUM")
    print(f"Wrote {DEMO_DB} ({DEMO_DB.stat().st_size / 1e6:.1f} MB): {counts}")


if __name__ == "__main__":
    main()
