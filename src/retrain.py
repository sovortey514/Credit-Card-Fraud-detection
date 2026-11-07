"""Check analyst feedback and prepare the model retraining workflow."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "fraud_detection.db"
MODEL_PATH = ROOT / "models" / "catboost_fraud_model.joblib"


def check_and_retrain(min_new_labels: int = 50) -> bool:
    """Check whether enough analyst labels exist for a safe retraining run.

    The current transaction table intentionally stores prediction metadata but
    not the original V1-V28 feature vector. Until those features are persisted,
    this function refuses to overwrite the production model with incomplete
    training data.
    """
    if min_new_labels < 1:
        raise ValueError("min_new_labels must be at least 1")
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return False

    with sqlite3.connect(DB_PATH) as connection:
        labeled = pd.read_sql_query(
            """
            SELECT *
            FROM transaction_logs
            WHERE confirmed_label IS NOT NULL
            """,
            connection,
        )

    print(f"Total confirmed analyst labels available: {len(labeled)}")
    if len(labeled) < min_new_labels:
        print(
            "Insufficient labeled data to trigger retraining "
            f"(requires at least {min_new_labels})."
        )
        return False

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Existing CatBoost model not found: {MODEL_PATH}")
    joblib.load(MODEL_PATH)

    required_feature_columns = {"Time", "Amount"} | {
        f"V{i}" for i in range(1, 29)
    }
    missing = sorted(required_feature_columns - set(labeled.columns))
    print(
        "Retraining was not performed: analyst logs are missing the original "
        f"model features {missing}. Persist the transaction feature payload "
        "before enabling automatic model updates."
    )
    return False


if __name__ == "__main__":
    check_and_retrain(min_new_labels=10)
