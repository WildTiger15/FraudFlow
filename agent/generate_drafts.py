"""Draft cases for a random sample of alerts, run the fact checks, and save them for review.

Usage: python -m agent.generate_drafts [--count 20]
Uses Claude if ANTHROPIC_API_KEY is set, otherwise the clearly labelled no-AI template.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

from agent.case_builder import build_case
from agent.checks import check_draft, final_confidence
from agent.drafter import draft_case
from config import DRAFT_SAMPLE_SIZE, RANDOM_SEED, ROOT
from db import connect
from results import write_section

EXAMPLES_DIR = ROOT / "outputs" / "example_drafts"


def pick_alerts(conn, count, seed=RANDOM_SEED):
    """Random alerts not yet drafted, spread across rules / anomaly / both."""
    alerts = pd.read_sql("SELECT alert_id, flagged_by FROM alerts WHERE status = 'new'", conn)
    groups = sorted(alerts["flagged_by"].unique())
    per_group = max(1, count // len(groups))
    picked = []
    for group in groups:
        pool = alerts[alerts["flagged_by"] == group]
        picked += pool.sample(min(per_group, len(pool)), random_state=seed)["alert_id"].tolist()
    leftover = alerts[~alerts["alert_id"].isin(picked)]
    picked += leftover.sample(max(0, count - len(picked)), random_state=seed)["alert_id"].tolist()
    return sorted(picked[:count])


def draft_and_store(conn, alert_id, client=None):
    facts = build_case(conn, alert_id)
    draft, drafted_by = draft_case(facts, client)
    check = check_draft(draft, facts)
    confidence = final_confidence(draft, check)
    case_id = "C-" + alert_id
    conn.execute(
        """INSERT OR REPLACE INTO cases (case_id, alert_id, facts_json, draft_json, drafted_by, check_passed,
           check_failures, confidence, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending_review', ?)""",
        (case_id, alert_id, json.dumps(facts), json.dumps(draft), drafted_by, int(check["passed"]),
         json.dumps(check["failures"]), confidence, datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    conn.execute("UPDATE alerts SET status = 'drafted' WHERE alert_id = ?", (alert_id,))
    conn.commit()
    return {"case_id": case_id, "drafted_by": drafted_by, "passed": check["passed"],
            "failures": check["failures"], "confidence": confidence, "draft": draft, "facts": facts}


def draft_to_markdown(result):
    d, f = result["draft"], result["facts"]
    label = "LOW CONFIDENCE: review carefully" if result["confidence"] == "low" else "Checks passed"
    lines = [f"# Case {result['case_id']} ({label})", "",
             f"Drafted by: `{result['drafted_by']}`. Synthetic PaySim data. A person must approve, edit or reject.", "",
             f"**Summary.** {d['summary']}", "", f"**What happened.** {d['what_happened']}", "",
             f"**Why flagged.** {d['why_flagged']}", "", "**What to check next**"]
    lines += [f"* {item}" for item in d["what_to_check_next"]]
    lines += ["", "**Report fields (UTR style)**", ""]
    lines += [f"* {k.replace('_', ' ').capitalize()}: {v if isinstance(v, str) else ', '.join(v)}"
              for k, v in d["report_fields"].items()]
    lines += ["", f"**Missing information:** {', '.join(d['missing_information']) or 'none listed'}",
              f"**Fact check failures:** {'; '.join(result['failures']) or 'none'}",
              "", f"Flagged transaction: {f['flagged_transaction']['tx_id']}; alert reasons: {len(f['reasons'])}"]
    return "\n".join(lines) + "\n"


def summary_markdown(results):
    n = len(results)
    passed = sum(r["passed"] for r in results)
    low = sum(r["confidence"] == "low" for r in results)
    by = Counter(r["drafted_by"] for r in results)
    failure_kinds = Counter(f.split(":")[0] for r in results for f in r["failures"])
    lines = ["## 3. AI case drafts", "",
             f"* Alerts drafted in this run: **{n}** (random sample spread across rules / anomaly / both, seed {RANDOM_SEED}).",
             "* Drafted by: " + ", ".join(f"`{k}` {v}" for k, v in by.items()),
             f"* Passed all automatic fact checks: **{passed} / {n}**",
             f"* Marked LOW CONFIDENCE (failed a check, or the drafter said low): **{low} / {n}**"]
    if failure_kinds:
        lines.append("* Check failures by type: " + "; ".join(f"{k} ({v})" for k, v in failure_kinds.items()))
    if any(k.startswith("template") for k in by):
        lines.append("* NOTE: `template_no_ai` drafts were made WITHOUT AI because no ANTHROPIC_API_KEY was set. "
                     "They show the pipeline and checks working, not AI quality. Rerun with a key for AI drafts.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=DRAFT_SAMPLE_SIZE)
    args = parser.parse_args()
    conn = connect()
    results = [draft_and_store(conn, alert_id) for alert_id in pick_alerts(conn, args.count)]
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for result in results[:3]:
        (EXAMPLES_DIR / f"{result['case_id']}.md").write_text(draft_to_markdown(result), encoding="utf-8")
    text = summary_markdown(results)
    write_section("drafting", text)
    print(text)


if __name__ == "__main__":
    main()
