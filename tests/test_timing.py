"""Timing study helpers. Uses made-up test numbers only inside the test, never in results."""
import pandas as pd
from scipy import stats

from timing.analyze import timing_markdown, welch_interval
from timing.review_session import assigned_mode


def test_assignment_is_stable_and_mixed():
    ids = [f"C-A{i:06d}" for i in range(200)]
    modes = [assigned_mode(i) for i in ids]
    assert modes == [assigned_mode(i) for i in ids]
    assert 60 < modes.count("manual") < 140


def test_welch_interval_matches_scipy():
    a = pd.Series([10.0, 12, 9, 14, 11])
    b = pd.Series([6.0, 7, 5, 8, 6, 7])
    diff, low, high = welch_interval(a, b)
    res = stats.ttest_ind(a, b, equal_var=False)
    ci = res.confidence_interval(0.95)
    assert abs(diff - (a.mean() - b.mean())) < 1e-9
    assert abs(low - ci.low) < 1e-9 and abs(high - ci.high) < 1e-9


def test_small_sample_is_flagged(monkeypatch):
    monkeypatch.setattr("timing.analyze.connect", lambda: None)
    monkeypatch.setattr("timing.analyze.pd.read_sql", lambda *a, **k: pd.DataFrame({"case_id": [], "drafted_by": []}))
    log = pd.DataFrame({"mode": ["manual"] * 3 + ["assisted"] * 3, "seconds": [600, 540, 660, 300, 240, 360],
                        "reviewer": ["R"] * 6, "decision": ["escalate"] * 3 + ["approve", "edit", "reject"],
                        "edit_size": ["", "", "", "none", "small", ""], "case_id": list("abcdef")})
    text = timing_markdown(log)
    assert "WARNING: fewer than 15" in text
    assert "approved without edits 1" in text and "draft rejected 1" in text
