"""Fit and serialize the credit-card preprocessing pipeline."""

from pathlib import Path
import sys

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.fraud_detection.preprocessing_pipeline import build_creditcard_preprocessing_pipeline


TRAIN_PATH = ROOT / "data" / "processed" / "creditcard_train.parquet"
MODEL_PATH = ROOT / "models" / "creditcard_preprocessing.joblib"


def main() -> None:
    train = pd.read_parquet(TRAIN_PATH)
    pipeline = build_creditcard_preprocessing_pipeline().fit(train)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Saved fitted preprocessing pipeline to {MODEL_PATH}")


if __name__ == "__main__":
    main()
