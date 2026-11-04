"""Anomaly detection with an Isolation Forest.

An Isolation Forest builds many random trees that keep splitting the data.
Unusual rows get isolated after only a few splits, so a short average path = more unusual.
It never sees the fraud labels: it only learns what "normal" looks like.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from config import RANDOM_SEED, SCREENED_TYPES

# Share of screened transactions we are willing to send to investigators.
ALERT_RATE = 0.01

FEATURES = [
    "log_amount",            # how big the transaction is
    "is_transfer",           # TRANSFER (1) or CASH_OUT (0)
    "share_of_balance",      # amount / sender balance before (capped)
    "sender_left_share",     # sender balance after / before
    "receiver_change_ratio", # how much the receiver balance moved, relative to the amount
    "amount_vs_normal",      # amount / account's earlier average (1 if no history)
    "receiver_tx_today",     # how many transactions the receiver had that day
    "hour",                  # hour of the simulated day
]


def build_features(df):
    """Simple per account and per transaction features. Needs add_account_history() columns."""
    feats = pd.DataFrame(index=df.index)
    feats["log_amount"] = np.log1p(df["amount"])
    feats["is_transfer"] = (df["type"] == "TRANSFER").astype(int)
    feats["share_of_balance"] = (df["amount"] / (df["oldbalanceOrg"] + 1)).clip(0, 10)
    feats["sender_left_share"] = (df["newbalanceOrig"] / (df["oldbalanceOrg"] + 1)).clip(0, 10)
    change = df["newbalanceDest"] - df["oldbalanceDest"]
    feats["receiver_change_ratio"] = (change / (df["amount"] + 1)).clip(-10, 10)
    prior_mean = df["dest_prior_mean"].fillna(df["orig_prior_mean"])
    feats["amount_vs_normal"] = (df["amount"] / prior_mean).replace([np.inf, -np.inf], np.nan).fillna(1).clip(0, 1000)
    feats["receiver_tx_today"] = df.groupby(["nameDest", "day"])["tx_id"].transform("size")
    feats["hour"] = df["hour"]
    return feats[FEATURES]


def score_anomalies(df_with_history, alert_rate=ALERT_RATE):
    """Fit the forest on screened transactions; return tx_id, score and flag.

    Higher anomaly_score = more unusual. The top `alert_rate` share is flagged.
    """
    all_feats = build_features(df_with_history)
    mask = df_with_history["type"].isin(SCREENED_TYPES)
    feats = all_feats[mask]
    model = IsolationForest(n_estimators=200, contamination=alert_rate, random_state=RANDOM_SEED, n_jobs=-1)
    model.fit(feats)
    scores = -model.score_samples(feats)  # flip sign so bigger = stranger
    return pd.DataFrame({
        "tx_id": df_with_history.loc[mask, "tx_id"].to_numpy(),
        "anomaly_score": scores,
        "anomaly_flag": model.predict(feats) == -1,
    })
