"""Shared test fixtures: a tiny in-memory-style SQLite DB with a few synthetic transactions."""
import pandas as pd
import pytest

import db
from data.load_data import save_to_sqlite

ROWS = [
    # step, type, amount, orig, oldOrg, newOrg, dest, oldDest, newDest, isFraud
    (1, "PAYMENT", 120.50, "C100", 500.0, 379.5, "M900", 0, 0, 0),
    (2, "TRANSFER", 250000.00, "C200", 250000.0, 0.0, "C300", 0.0, 0.0, 1),
    (3, "CASH_OUT", 250000.00, "C300", 250000.0, 0.0, "C400", 1000.0, 251000.0, 1),
    (4, "CASH_IN", 999.99, "C300", 0.0, 999.99, "C500", 0, 0, 0),
]


@pytest.fixture
def conn(tmp_path):
    df = pd.DataFrame(ROWS, columns=["step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
                                     "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud"])
    df["isFlaggedFraud"] = 0
    df.insert(0, "tx_id", [f"T{i + 1:07d}" for i in range(len(df))])
    df["day"] = (df["step"] - 1) // 24 + 1
    df["hour"] = (df["step"] - 1) % 24
    connection = db.connect(tmp_path / "test.db")
    save_to_sqlite(df, connection)
    connection.execute(
        "INSERT INTO alerts VALUES ('A000001', 'T0000002', 'C200', 'C300', 2, 1, 250000.0, 'rules', "
        "'ACCOUNT_DRAINED,PASS_THROUGH', 'ACCOUNT_DRAINED: whole balance moved.\nPASS_THROUGH: balance stayed 0.', "
        "0.51, 'new')")
    connection.commit()
    yield connection
    connection.close()
