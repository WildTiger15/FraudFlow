"""SQLite helpers. One small database file holds transactions, alerts, cases and decisions."""
import sqlite3

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    tx_id TEXT NOT NULL,
    account TEXT NOT NULL,
    counterparty TEXT NOT NULL,
    step INTEGER NOT NULL,
    day INTEGER NOT NULL,
    amount REAL NOT NULL,
    flagged_by TEXT NOT NULL,          -- rules, anomaly or both
    rule_codes TEXT NOT NULL,          -- comma separated, may be empty
    reasons TEXT NOT NULL,             -- plain language, one per line
    anomaly_score REAL,
    status TEXT NOT NULL DEFAULT 'new' -- new, drafted, decided
);
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL UNIQUE,
    facts_json TEXT NOT NULL,          -- exactly what the drafter was given
    draft_json TEXT NOT NULL,
    drafted_by TEXT NOT NULL,          -- model name, or template_no_ai
    check_passed INTEGER NOT NULL,
    check_failures TEXT NOT NULL,
    confidence TEXT NOT NULL,          -- high or low
    status TEXT NOT NULL DEFAULT 'pending_review',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    decision TEXT NOT NULL,            -- approve, edit or reject
    reviewer TEXT NOT NULL,
    comment TEXT,
    edited_summary TEXT,
    review_seconds REAL,
    channel TEXT NOT NULL,             -- power_automate or fallback_page
    decided_at TEXT NOT NULL
);
"""


def connect(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
