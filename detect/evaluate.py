"""Run both detectors, measure them against the PaySim fraud labels, and save alerts.

Metrics (per screened transaction):
  recall    = fraud transactions flagged / all fraud transactions
  precision = fraud transactions flagged / all flagged transactions
  false alarms per 1,000 = flagged non-fraud / screened transactions * 1,000
Labels are ONLY used here, to measure. They are never given to the detectors or the AI.
"""
import pandas as pd

from config import SCREENED_TYPES
from db import connect
from detect.anomaly import score_anomalies
from detect.rules import REASONS, RULES, add_account_history, apply_rules
from results import write_section


def load_transactions(conn):
    return pd.read_sql("SELECT * FROM transactions", conn)


def metrics(flag, is_fraud):
    """Recall, precision and false alarms for one True/False flag column."""
    flagged = int(flag.sum())
    caught = int((flag & is_fraud).sum())
    false_alarms = flagged - caught
    total_fraud = int(is_fraud.sum())
    return {
        "alerts": flagged,
        "fraud_caught": caught,
        "total_fraud": total_fraud,
        "recall": caught / total_fraud if total_fraud else 0.0,
        "precision": caught / flagged if flagged else 0.0,
        "false_alarms": false_alarms,
        "false_alarms_per_1000": false_alarms / len(flag) * 1000,
    }


def build_results(df):
    """Combine rule hits and anomaly scores into one table per screened transaction."""
    hits = apply_rules(df)
    scores = score_anomalies(add_account_history(df))
    table = hits.merge(scores, on="tx_id")
    labels = df[["tx_id", "isFraud"]]
    table = table.merge(labels, on="tx_id")
    table["is_fraud"] = table["isFraud"] == 1
    table["combined_flag"] = table["rule_flag"] | table["anomaly_flag"]
    table["both_flag"] = table["rule_flag"] & table["anomaly_flag"]
    return table


def metrics_table(table):
    rows = {
        "Rules (any rule)": metrics(table["rule_flag"], table["is_fraud"]),
        "Anomaly detection (Isolation Forest)": metrics(table["anomaly_flag"], table["is_fraud"]),
        "Combined (rules OR anomaly)": metrics(table["combined_flag"], table["is_fraud"]),
        "Both agree (rules AND anomaly)": metrics(table["both_flag"], table["is_fraud"]),
    }
    for code, _, _ in RULES:
        rows[f"Rule only: {code}"] = metrics(table[code], table["is_fraud"])
    return rows


def save_alerts(table, df, conn):
    """Write every combined alert to the alerts table (status 'new')."""
    flagged = table[table["combined_flag"]].merge(
        df[["tx_id", "nameOrig", "nameDest", "step", "day", "amount"]], on="tx_id")
    flagged = flagged.sort_values(["step", "tx_id"]).reset_index(drop=True)
    alerts = pd.DataFrame({
        "alert_id": [f"A{i + 1:06d}" for i in range(len(flagged))],
        "tx_id": flagged["tx_id"],
        "account": flagged["nameOrig"],
        "counterparty": flagged["nameDest"],
        "step": flagged["step"],
        "day": flagged["day"],
        "amount": flagged["amount"],
        "flagged_by": flagged.apply(
            lambda r: "both" if r["rule_flag"] and r["anomaly_flag"] else ("rules" if r["rule_flag"] else "anomaly"),
            axis=1),
        "rule_codes": flagged["rule_codes"],
        "reasons": flagged.apply(lambda r: _reasons_text(r["rule_codes"], r["anomaly_flag"]), axis=1),
        "anomaly_score": flagged["anomaly_score"].round(4),
        "status": "new",
    })
    conn.execute("DELETE FROM alerts")
    alerts.to_sql("alerts", conn, if_exists="append", index=False)
    conn.commit()
    return alerts


def _reasons_text(rule_codes, anomaly_flag):
    reasons = [f"{code}: {REASONS[code]}" for code in rule_codes.split(",") if code]
    if anomaly_flag:
        reasons.append("ANOMALY: Isolation Forest ranked this transaction in the most unusual 1% of screened transactions.")
    return "\n".join(reasons)


def to_markdown(rows, n_screened, n_total, n_days):
    lines = [
        "## 2. Detection quality",
        "",
        f"* Transactions screened (TRANSFER and CASH_OUT): **{n_screened:,}** of {n_total:,} loaded, over {n_days} simulated days.",
        f"* Labelled fraud among screened: **{next(iter(rows.values()))['total_fraud']:,}** (every PaySim fraud is TRANSFER or CASH_OUT).",
        "* Measured per transaction against PaySim's `isFraud` label. Labels are never used by the detectors.",
        "* Rule thresholds were set by hand from AML patterns. After a first run flagged 82% of screened transactions, "
        "the ACCOUNT_DRAINED, VERY_LARGE_TRANSFER and MANY_SENDERS thresholds were revised once to keep alert volume "
        "manageable (see docs/DETECTION_NOTES.md). The labels were visible during that revision, so treat these numbers "
        "as optimistic: there is no separate held-out period yet.",
        "* The Isolation Forest flags the most unusual 1% of screened transactions.",
        "",
        "| Method | Alerts | Fraud caught | Recall | Precision | False alarms per 1,000 screened |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, m in rows.items():
        lines.append(
            f"| {name} | {m['alerts']:,} | {m['fraud_caught']:,} / {m['total_fraud']:,} | "
            f"{m['recall']:.1%} | {m['precision']:.1%} | {m['false_alarms_per_1000']:.1f} |")
    return "\n".join(lines)


def main():
    conn = connect()
    df = load_transactions(conn)
    table = build_results(df)
    rows = metrics_table(table)
    alerts = save_alerts(table, df, conn)
    text = to_markdown(rows, len(table), len(df), df["day"].nunique())
    text += f"\n\nAlerts saved for review: **{len(alerts):,}** (combined method). "
    text += "By source: " + ", ".join(f"{k} {v:,}" for k, v in alerts["flagged_by"].value_counts().items()) + "."
    write_section("detection", text)
    print(text)


if __name__ == "__main__":
    main()
