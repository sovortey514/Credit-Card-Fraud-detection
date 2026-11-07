"""Verify Credit Card feature engineering from the project root."""

from pathlib import Path

import pandas as pd

from src.features import engineer_features_creditcard


def main() -> None:
    project_root = Path(__file__).resolve().parent
    data_candidates = (
        project_root / "data" / "creditcard.csv",
        project_root / "data" / "raw" / "creditcard.csv",
    )
    data_path = next((path for path in data_candidates if path.exists()), None)
    if data_path is None:
        raise FileNotFoundError(
            "Credit Card dataset not found in data/ or data/raw/."
        )

    df = pd.read_csv(data_path)
    df_processed = engineer_features_creditcard(df)

    print("\nNew Feature Preview:")
    print(
        df_processed[
            [
                "Amount",
                "scaled_amount",
                "hour_of_day",
                "is_night_transaction",
                "log_amount",
            ]
        ].head()
    )


if __name__ == "__main__":
    main()
