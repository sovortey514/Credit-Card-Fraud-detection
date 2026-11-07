"""Verify the leakage-safe Credit Card resampling pipeline."""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src.features import engineer_features_creditcard
from src.sampling import prepare_splits_and_resample


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
    # Tomek-link cleanup is expensive on the full 284k-row dataset. Use a
    # stratified verification sample; production training can use all rows.
    if len(df) > 50_000:
        df, _ = train_test_split(
            df,
            train_size=50_000,
            random_state=42,
            stratify=df["Class"],
        )
        df = df.reset_index(drop=True)
        print(f"Using stratified verification sample: {len(df):,} rows")
    df_processed = engineer_features_creditcard(df)
    x_train_res, x_test, y_train_res, y_test = prepare_splits_and_resample(
        df_processed,
        target_col="Class",
        strategy="smote_tomek",
    )

    print("\n===== STEP 3 VERIFICATION =====")
    print(f"Resampled training features: {x_train_res.shape}")
    print(f"Untouched test features: {x_test.shape}")
    print(f"Resampled training labels: {y_train_res.shape}")
    print(f"Untouched test labels: {y_test.shape}")


if __name__ == "__main__":
    main()
