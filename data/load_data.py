"""Load a manageable slice of PaySim into SQLite and save a small sample CSV.

We keep the first SAMPLE_MAX_STEP simulated hours (3 days). A time slice keeps each
account's history together, which the rules and the case builder need.
"""
import pandas as pd

from config import RAW_CSV, SAMPLE_CSV, SAMPLE_MAX_STEP
from db import connect
from results import write_section


def read_slice(csv_path=RAW_CSV, max_step=SAMPLE_MAX_STEP):
    df = pd.read_csv(csv_path)
    # Stable transaction ID = row number in the original file, e.g. T0000001.
    df.insert(0, "tx_id", [f"T{i + 1:07d}" for i in range(len(df))])
    df = df[df["step"] <= max_step].copy()
    df["day"] = (df["step"] - 1) // 24 + 1
    df["hour"] = (df["step"] - 1) % 24
    return df


def save_to_sqlite(df, conn):
    df.to_sql("transactions", conn, if_exists="replace", index=False, chunksize=50_000)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_tx_id ON transactions(tx_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_orig ON transactions(nameOrig, step)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_dest ON transactions(nameDest, step)")
    conn.commit()


def main():
    df = read_slice()
    conn = connect()
    save_to_sqlite(df, conn)
    df.head(5000).to_csv(SAMPLE_CSV, index=False)

    by_type = df.groupby("type")["isFraud"].agg(["size", "sum"]).rename(
        columns={"size": "transactions", "sum": "labelled_fraud"})
    lines = [
        "## 1. Data",
        "",
        f"* Source: PaySim synthetic mobile money data (public, no real customers).",
        f"* Slice loaded: simulated hours 1 to {SAMPLE_MAX_STEP} (days 1 to {df['day'].max()}).",
        f"* Transactions loaded: {len(df):,}",
        f"* Labelled fraud transactions: {int(df['isFraud'].sum()):,} "
        f"({df['isFraud'].mean() * 100:.3f}% of all transactions)",
        f"* Distinct sending accounts: {df['nameOrig'].nunique():,}; distinct receiving accounts: {df['nameDest'].nunique():,}",
        "",
        "| Type | Transactions | Labelled fraud |",
        "|---|---:|---:|",
    ]
    for tx_type, row in by_type.iterrows():
        lines.append(f"| {tx_type} | {row['transactions']:,} | {row['labelled_fraud']:,} |")
    write_section("data", "\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
