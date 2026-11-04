"""Clear, explainable rules for common fraud and money laundering patterns.

Each rule looks at a table of transactions and returns True/False per row.
Each rule has a short code and a plain language reason an investigator can read.
Thresholds are constants at the top so they are easy to find and discuss.
"""
import pandas as pd

from config import SCREENED_TYPES

DRAIN_TOLERANCE = 0.01         # amount matches the whole balance within 1%
DRAIN_MIN_BALANCE = 10_000     # ignore tiny balances
REPORT_LIMIT = 10_000          # Canadian large cash reporting threshold
STRUCTURING_FLOOR = 9_000      # "just under" the limit means 9,000 to 9,999.99
STRUCTURING_MIN_COUNT = 2      # at least 2 such amounts for one account in one day
SPIKE_MULTIPLE = 10            # amount at least 10x the account's usual amount
SPIKE_MIN_HISTORY = 3          # need at least 3 earlier transactions to know "usual"
VERY_LARGE_AMOUNT = 2_500_000  # single transfer of 2.5 million or more (about the top 1% of transfers here)
MANY_SENDERS_MIN = 50          # receiving account paid by 50+ different senders in a day


def account_drained(df):
    """The whole balance moved out in one go (typical after account takeover).

    "Whole balance" means the amount equals the balance before, within 1%.
    """
    gap = (df["amount"] - df["oldbalanceOrg"]).abs()
    return (df["oldbalanceOrg"] >= DRAIN_MIN_BALANCE) & (gap <= DRAIN_TOLERANCE * df["oldbalanceOrg"])


def pass_through(df):
    """Money sent to a customer account whose balance did not change: it passed straight through."""
    receiver_is_customer = df["nameDest"].str.startswith("C")
    unchanged = (df["oldbalanceDest"] == 0) & (df["newbalanceDest"] == 0)
    return receiver_is_customer & unchanged & (df["amount"] > 0)


def structuring(df):
    """Several amounts just under the reporting limit by the same account on the same day."""
    near_limit = (df["amount"] >= STRUCTURING_FLOOR) & (df["amount"] < REPORT_LIMIT)
    flagged = pd.Series(False, index=df.index)
    for account_col in ("nameOrig", "nameDest"):
        counts = df[near_limit].groupby([account_col, "day"])["tx_id"].transform("size")
        flagged |= (counts >= STRUCTURING_MIN_COUNT).reindex(df.index, fill_value=False)
    return flagged


def add_account_history(df):
    """Add each account's average amount BEFORE this transaction (sender and receiver side).

    Only earlier transactions are used, so the rule never looks into the future.
    """
    rows = []
    for role, col in (("orig", "nameOrig"), ("dest", "nameDest")):
        part = df[["tx_id", "step", col, "amount"]].rename(columns={col: "account"})
        part["role"] = role
        rows.append(part)
    long = pd.concat(rows).sort_values(["account", "step", "tx_id"], kind="stable")
    grouped = long.groupby("account")["amount"]
    long["prior_count"] = grouped.cumcount()
    long["prior_mean"] = (grouped.cumsum() - long["amount"]) / long["prior_count"].where(long["prior_count"] > 0)
    out = df.copy()
    for role in ("orig", "dest"):
        side = long[long["role"] == role].set_index("tx_id")[["prior_count", "prior_mean"]]
        side.columns = [f"{role}_prior_count", f"{role}_prior_mean"]
        out = out.join(side, on="tx_id")
    return out


def spike_vs_normal(df):
    """Amount far above what the sender or receiver usually moves."""
    flagged = pd.Series(False, index=df.index)
    for role in ("orig", "dest"):
        enough_history = df[f"{role}_prior_count"] >= SPIKE_MIN_HISTORY
        flagged |= enough_history & (df["amount"] >= SPIKE_MULTIPLE * df[f"{role}_prior_mean"])
    return flagged


def very_large_transfer(df):
    """A single transfer of a very large amount."""
    return (df["type"] == "TRANSFER") & (df["amount"] >= VERY_LARGE_AMOUNT)


def many_senders(df):
    """Receiving account paid by many different senders in one day (possible money mule)."""
    senders = df.groupby(["nameDest", "day"])["nameOrig"].transform("nunique")
    return senders >= MANY_SENDERS_MIN


# (code, function, reason shown to the investigator)
RULES = [
    ("ACCOUNT_DRAINED", account_drained,
     f"Sender moved their entire balance (amount equals the balance within {DRAIN_TOLERANCE:.0%}, balance {DRAIN_MIN_BALANCE:,}+) in one transaction."),
    ("PASS_THROUGH", pass_through,
     "Receiving customer account balance stayed at 0 after receiving money: funds appear to pass straight through."),
    ("STRUCTURING", structuring,
     f"{STRUCTURING_MIN_COUNT}+ amounts between {STRUCTURING_FLOOR:,} and {REPORT_LIMIT:,} for the same account on the same day (just under the reporting limit)."),
    ("SPIKE_VS_NORMAL", spike_vs_normal,
     f"Amount is at least {SPIKE_MULTIPLE}x the account's average over its earlier transactions ({SPIKE_MIN_HISTORY}+ needed)."),
    ("VERY_LARGE_TRANSFER", very_large_transfer,
     f"Single transfer of {VERY_LARGE_AMOUNT:,} or more."),
    ("MANY_SENDERS", many_senders,
     f"Receiving account was paid by {MANY_SENDERS_MIN}+ different senders on the same day."),
]
REASONS = {code: reason for code, _, reason in RULES}


def screened(df):
    """Only money-leaving types are screened (TRANSFER, CASH_OUT)."""
    return df[df["type"].isin(SCREENED_TYPES)]


def apply_rules(df):
    """Return one row per screened transaction with a True/False column per rule.

    History and many-senders counts are computed on ALL transactions first,
    then only the screened types are kept.
    """
    full = add_account_history(df)
    hits = pd.DataFrame({"tx_id": full["tx_id"]})
    for code, rule, _ in RULES:
        hits[code] = rule(full).to_numpy()
    hits = hits[full["type"].isin(SCREENED_TYPES).to_numpy()]
    codes = [code for code, _, _ in RULES]
    hits["rule_codes"] = hits[codes].apply(lambda row: ",".join(c for c in codes if row[c]), axis=1)
    hits["rule_flag"] = hits[codes].any(axis=1)
    return hits.reset_index(drop=True)
