import pandas as pd

from detect.evaluate import metrics


def test_metrics_match_hand_calculation():
    # 10 transactions, 2 fraud; we flag 4, of which 1 is fraud.
    flag = pd.Series([True, True, True, True] + [False] * 6)
    fraud = pd.Series([True, False, False, False, True] + [False] * 5)
    m = metrics(flag, fraud)
    assert m["recall"] == 0.5
    assert m["precision"] == 0.25
    assert m["false_alarms"] == 3
    assert m["false_alarms_per_1000"] == 300
