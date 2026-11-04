"""Gather the facts for one alert: the flagged transaction, recent activity and why it was flagged.

The output ("facts") is the ONLY information the AI drafter sees. It never includes the
PaySim fraud labels (isFraud, isFlaggedFraud): that would be cheating and is tested.
"""
LOOKBACK_STEPS = 72      # look back up to 72 simulated hours
MAX_RECENT = 20          # cap each activity list so drafts stay short

TX_FIELDS = ["tx_id", "day", "hour", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
             "nameDest", "oldbalanceDest", "newbalanceDest"]
LABEL_FIELDS = ("isFraud", "isFlaggedFraud")


def _tx_dict(row):
    tx = {field: row[field] for field in TX_FIELDS}
    tx["sender"] = tx.pop("nameOrig")
    tx["receiver"] = tx.pop("nameDest")
    tx["sender_balance_before"] = round(tx.pop("oldbalanceOrg"), 2)
    tx["sender_balance_after"] = round(tx.pop("newbalanceOrig"), 2)
    tx["receiver_balance_before"] = round(tx.pop("oldbalanceDest"), 2)
    tx["receiver_balance_after"] = round(tx.pop("newbalanceDest"), 2)
    tx["amount"] = round(tx["amount"], 2)
    return tx


def recent_activity(conn, account, up_to_step):
    """All transactions where the account was sender or receiver, in the lookback window."""
    rows = conn.execute(
        f"""SELECT {', '.join(TX_FIELDS)} FROM transactions
            WHERE (nameOrig = ? OR nameDest = ?) AND step BETWEEN ? AND ?
            ORDER BY step DESC, tx_id DESC LIMIT ?""",
        (account, account, up_to_step - LOOKBACK_STEPS, up_to_step, MAX_RECENT),
    ).fetchall()
    return [_tx_dict(r) for r in reversed(rows)]


def summarise(account, txs):
    """Pre-computed totals, so the AI never has to do arithmetic itself."""
    sent = [t["amount"] for t in txs if t["sender"] == account]
    received = [t["amount"] for t in txs if t["receiver"] == account]
    return {
        "transaction_count": len(txs),
        "sent_count": len(sent),
        "sent_total": round(sum(sent), 2),
        "received_count": len(received),
        "received_total": round(sum(received), 2),
        "distinct_counterparties": len({t["receiver"] if t["sender"] == account else t["sender"] for t in txs}),
    }


def build_case(conn, alert_id):
    alert = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
    if alert is None:
        raise KeyError(f"No alert {alert_id}")
    flagged = conn.execute(f"SELECT {', '.join(TX_FIELDS)}, step FROM transactions WHERE tx_id = ?",
                           (alert["tx_id"],)).fetchone()
    sender_txs = recent_activity(conn, alert["account"], flagged["step"])
    receiver_txs = recent_activity(conn, alert["counterparty"], flagged["step"])
    return {
        "alert_id": alert["alert_id"],
        "flagged_by": alert["flagged_by"],
        "reasons": [r for r in alert["reasons"].split("\n") if r],
        "flagged_transaction": _tx_dict(flagged),
        "subject_account": alert["account"],
        "counterparty_account": alert["counterparty"],
        "lookback": f"up to {LOOKBACK_STEPS} simulated hours before the flagged transaction, max {MAX_RECENT} per account",
        "subject_recent_activity": sender_txs,
        "subject_summary": summarise(alert["account"], sender_txs),
        "counterparty_recent_activity": receiver_txs,
        "counterparty_summary": summarise(alert["counterparty"], receiver_txs),
    }


def case_transaction_ids(facts):
    """Every transaction ID the drafter was shown (used by the checks)."""
    ids = {facts["flagged_transaction"]["tx_id"]}
    for key in ("subject_recent_activity", "counterparty_recent_activity"):
        ids.update(t["tx_id"] for t in facts[key])
    return ids
