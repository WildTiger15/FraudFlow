"""Small hand-made transactions to check that each rule fires when it should and not otherwise."""
import pandas as pd

from detect import rules


def make_tx(rows):
    base = {"step": 1, "type": "TRANSFER", "amount": 100.0, "nameOrig": "C1", "oldbalanceOrg": 1000.0,
            "newbalanceOrig": 900.0, "nameDest": "C2", "oldbalanceDest": 50.0, "newbalanceDest": 150.0,
            "isFraud": 0}
    df = pd.DataFrame([{**base, **r} for r in rows])
    df["tx_id"] = [f"T{i:07d}" for i in range(len(df))]
    df["day"] = (df["step"] - 1) // 24 + 1
    df["hour"] = (df["step"] - 1) % 24
    return df


def test_account_drained_needs_whole_balance():
    df = make_tx([
        {"amount": 50_000, "oldbalanceOrg": 50_000, "newbalanceOrig": 0},   # whole balance
        {"amount": 40_000, "oldbalanceOrg": 50_000, "newbalanceOrig": 0},   # only 80%
        {"amount": 5_000, "oldbalanceOrg": 5_000, "newbalanceOrig": 0},     # balance too small
    ])
    assert rules.account_drained(df).tolist() == [True, False, False]


def test_pass_through_only_for_customer_accounts():
    df = make_tx([
        {"oldbalanceDest": 0, "newbalanceDest": 0},
        {"oldbalanceDest": 0, "newbalanceDest": 0, "nameDest": "M9"},   # merchant
        {"oldbalanceDest": 0, "newbalanceDest": 100},
    ])
    assert rules.pass_through(df).tolist() == [True, False, False]


def test_structuring_needs_two_near_limit_amounts_same_day():
    df = make_tx([
        {"nameOrig": "C5", "amount": 9_500},
        {"nameOrig": "C5", "amount": 9_900},
        {"nameOrig": "C6", "amount": 9_500},                 # only one
        {"nameOrig": "C7", "amount": 9_500},
        {"nameOrig": "C7", "amount": 9_500, "step": 30},     # next day
    ])
    df["nameDest"] = [f"C{100 + i}" for i in range(len(df))]
    assert rules.structuring(df).tolist() == [True, True, False, False, False]


def test_spike_uses_only_earlier_transactions():
    rows = [{"nameOrig": "C1", "nameDest": f"D{i}", "amount": 100, "step": i + 1} for i in range(3)]
    rows.append({"nameOrig": "C1", "nameDest": "D9", "amount": 5_000, "step": 10})
    df = rules.add_account_history(make_tx(rows))
    assert rules.spike_vs_normal(df).tolist() == [False, False, False, True]


def test_very_large_transfer_only_for_transfers():
    df = make_tx([{"amount": 3_000_000}, {"amount": 3_000_000, "type": "CASH_OUT"}, {"amount": 10}])
    assert rules.very_large_transfer(df).tolist() == [True, False, False]


def test_apply_rules_skips_unscreened_types_and_lists_codes():
    df = make_tx([
        {"type": "PAYMENT", "nameDest": "M1"},
        {"amount": 50_000, "oldbalanceOrg": 50_000, "newbalanceOrig": 0, "oldbalanceDest": 0, "newbalanceDest": 0},
    ])
    hits = rules.apply_rules(df)
    assert len(hits) == 1
    assert hits.loc[0, "rule_codes"] == "ACCOUNT_DRAINED,PASS_THROUGH"
    assert bool(hits.loc[0, "rule_flag"])
