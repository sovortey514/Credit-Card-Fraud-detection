"""Verify the end-to-end Credit Card model-training pipeline."""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src.features import engineer_features_creditcard
from src.sampling import prepare_splits_and_resample
from src.train import train_and_evaluate_models


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
    train_and_evaluate_models(
        x_train_res,
        x_test,
        y_train_res,
        y_test,
        model_dir=str(project_root / "models"),
    )


if __name__ == "__main__":
    main()
