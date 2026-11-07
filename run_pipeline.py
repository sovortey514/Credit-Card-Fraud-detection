"""Run the Credit Card fraud pipeline from data preparation to feedback."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src.database import init_db, log_transaction, update_analyst_feedback
from src.features import engineer_features_creditcard
from src.retrain import check_and_retrain
from src.sampling import prepare_splits_and_resample
from src.train import train_and_evaluate_models


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-size",
        type=int,
        default=50_000,
        help="Stratified rows for a practical run; use 0 for the full dataset.",
    )
    args = parser.parse_args()

    data_candidates = (
        ROOT / "data" / "creditcard.csv",
        ROOT / "data" / "raw" / "creditcard.csv",
    )
    data_path = next((path for path in data_candidates if path.exists()), None)
    if data_path is None:
        raise FileNotFoundError("Credit Card dataset not found in data/ or data/raw/")

    print("=" * 66)
    print(" STARTING END-TO-END HYBRID FRAUD DETECTION PIPELINE RUNNER")
    print("=" * 66)

    print("\n[Step 1] Loading raw transaction dataset...")
    df = pd.read_csv(data_path)
    if args.sample_size > 0 and len(df) > args.sample_size:
        df, _ = train_test_split(
            df,
            train_size=args.sample_size,
            random_state=42,
            stratify=df["Class"],
        )
        df = df.reset_index(drop=True)
        print(f"Using stratified verification sample: {len(df):,} transactions.")
    else:
        print(f"Loaded {len(df):,} transactions.")

    print("\n[Step 2] Engineering temporal and scale features...")
    df_processed = engineer_features_creditcard(df)

    print("\n[Step 3] Splitting data and applying SMOTE-Tomek...")
    x_train_res, x_test, y_train_res, y_test = prepare_splits_and_resample(
        df_processed,
        target_col="Class",
        strategy="smote_tomek",
    )

    print("\n[Step 4] Training CatBoost and XGBoost models...")
    train_and_evaluate_models(x_train_res, x_test, y_train_res, y_test)

    print("\n[Step 5] Initializing SQLite database and logging prediction...")
    init_db()
    transaction_id = log_transaction(
        amount=2450.00,
        status="REJECTED",
        decision="FLAGGED_BY_ML",
        risk_score=0.92,
        reasons=["Feature 'scaled_amount' increased risk score"],
    )

    print("\n[Step 6] Updating analyst feedback and testing retraining loop...")
    update_analyst_feedback(transaction_id, confirmed_label=1)
    retrained = check_and_retrain(min_new_labels=1)
    print(f"Retraining performed: {retrained}")

    print("\n" + "=" * 66)
    print(" PIPELINE EXECUTION COMPLETED")
    print("=" * 66)


if __name__ == "__main__":
    main()
