"""Timed review session for the timing study. YOU do the reviews; this only shows cases and times them.

  python -m timing.review_session --mode manual   --reviewer "Your Name"
  python -m timing.review_session --mode assisted --reviewer "Your Name"

manual   = you see only the raw data (alert reasons + transactions) and write your own short summary.
assisted = you see the same raw data PLUS FraudFlow's draft, and approve / edit / reject it.
Each case is randomly assigned to one mode only (fixed seed), so you never review the same case twice.
The clock starts when the case is printed and stops when you enter your decision.
Results go to timing/timing_log.csv.
"""
import argparse
import csv
import json
import random
import time
from datetime import datetime, timezone

from config import RANDOM_SEED, ROOT
from db import connect

LOG = ROOT / "timing" / "timing_log.csv"
FIELDS = ["logged_at", "case_id", "alert_id", "mode", "seconds", "decision", "edit_size", "reviewer", "notes"]
ASSISTED_CHOICES = {"a": ("approve", "none"), "s": ("edit", "small"), "l": ("edit", "large"), "r": ("reject", "")}
MANUAL_CHOICES = {"e": "escalate", "c": "close_no_action"}


def assigned_mode(case_id, seed=RANDOM_SEED):
    """Random but repeatable: each case belongs to exactly one mode."""
    return "manual" if random.Random(f"{seed}-{case_id}").random() < 0.5 else "assisted"


def done_case_ids():
    if not LOG.exists():
        return set()
    with LOG.open(newline="", encoding="utf-8") as f:
        return {row["case_id"] for row in csv.DictReader(f)}


def next_case(conn, mode):
    done = done_case_ids()
    for row in conn.execute("SELECT * FROM cases ORDER BY case_id"):
        if row["case_id"] not in done and assigned_mode(row["case_id"]) == mode:
            return row
    return None


def print_raw(facts):
    print("\nALERT REASONS")
    for reason in facts["reasons"]:
        print("  -", reason)
    for title, key in (("SUBJECT", "subject"), ("COUNTERPARTY", "counterparty")):
        account = facts[f"{key}_account"]
        print(f"\n{title} ACCOUNT {account} - recent transactions")
        print(f"  {'ID':9} {'day':>3} {'hr':>2} {'type':9} {'amount':>13}  sender -> receiver  (sender bal before->after | receiver bal before->after)")
        for t in facts[f"{key}_recent_activity"]:
            print(f"  {t['tx_id']:9} {t['day']:>3} {t['hour']:>2} {t['type']:9} {t['amount']:>13,.2f}  {t['sender']} -> {t['receiver']}"
                  f"  ({t['sender_balance_before']:,.2f}->{t['sender_balance_after']:,.2f} | "
                  f"{t['receiver_balance_before']:,.2f}->{t['receiver_balance_after']:,.2f})")
    print(f"\nFLAGGED TRANSACTION: {facts['flagged_transaction']['tx_id']}")


def print_draft(row):
    draft = json.loads(row["draft_json"])
    label = "LOW CONFIDENCE - check every fact" if row["confidence"] == "low" else "Checks passed"
    print(f"\n=== FRAUDFLOW DRAFT ({label}; drafted by {row['drafted_by']}) ===")
    print("Summary:", draft["summary"])
    print("What happened:", draft["what_happened"])
    print("Why flagged:", draft["why_flagged"])
    print("Check next:", "; ".join(draft["what_to_check_next"]))
    print("Narrative:", draft["report_fields"]["narrative"])
    failures = json.loads(row["check_failures"])
    if failures:
        print("Fact check failures:", "; ".join(failures))


def ask(prompt, choices):
    while True:
        answer = input(prompt).strip().lower()
        if answer in choices:
            return answer


def log_row(row):
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)


def review_one(conn, mode, reviewer):
    row = next_case(conn, mode)
    if row is None:
        print(f"No more cases assigned to '{mode}'. Draft more with: python -m agent.generate_drafts --count 40")
        return False
    facts = json.loads(row["facts_json"])
    input(f"\nCase {row['case_id']} ({mode}). Press Enter to START the clock...")
    start = time.perf_counter()
    print_raw(facts)
    if mode == "manual":
        print("\nWrite your own 2-3 sentence summary in your notes file, citing transaction IDs.")
        choice = MANUAL_CHOICES[ask("Done? Decision: [e]scalate / [c]lose with no action > ", MANUAL_CHOICES)]
        decision, edit_size = choice, ""
    else:
        print_draft(row)
        key = ask("\nDecision: [a]pprove as is / [s]mall edits / [l]arge edits / [r]eject draft > ", ASSISTED_CHOICES)
        decision, edit_size = ASSISTED_CHOICES[key]
    seconds = round(time.perf_counter() - start, 1)
    notes = input("Optional note (not timed): ").strip()
    log_row({"logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "case_id": row["case_id"],
             "alert_id": row["alert_id"], "mode": mode, "seconds": seconds, "decision": decision,
             "edit_size": edit_size, "reviewer": reviewer, "notes": notes})
    print(f"Logged {seconds} s.")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["manual", "assisted"], required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--count", type=int, default=5, help="cases in this sitting")
    args = parser.parse_args()
    conn = connect()
    for _ in range(args.count):
        if not review_one(conn, args.mode, args.reviewer):
            break


if __name__ == "__main__":
    main()
