"""Quick validation report for the Credit Card Fraud Detection dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"Time", "Amount", "Class"}


def verify_dataset(path: Path) -> int:
    if not path.exists():
        print(f"ERROR: dataset not found: {path}")
        return 1

    df = pd.read_csv(path)
    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    print("===== DATASET VERIFICATION =====")
    print(f"File: {path}")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Column names: {', '.join(df.columns)}")
    print(f"Missing values: {int(df.isna().sum().sum()):,}")

    if missing_columns:
        print(f"ERROR: missing required columns: {sorted(missing_columns)}")
        return 1

    class_counts = df["Class"].value_counts().sort_index()
    print("\nClass distribution:")
    for label, count in class_counts.items():
        percentage = count / len(df) * 100
        description = "fraud" if label == 1 else "legitimate" if label == 0 else "unknown"
        print(f"  {label} ({description:10}): {count:>8,} ({percentage:.4f}%)")

    fraud_rate = float(df["Class"].mean() * 100)
    print(f"\nFraud rate: {fraud_rate:.4f}%")
    print(f"Amount range: {df['Amount'].min():.2f} to {df['Amount'].max():.2f}")
    print("Dataset verification completed successfully.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/raw/creditcard.csv"),
        help="Path to the Credit Card CSV file",
    )
    args = parser.parse_args()
    raise SystemExit(verify_dataset(args.data))


if __name__ == "__main__":
    main()
