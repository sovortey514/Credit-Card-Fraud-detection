"""Create a separate, diagram-aligned credit-card preprocessing dataset.

The existing research pipeline and its model artifacts are intentionally unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "processed"
OUTPUT = ROOT / "data" / "diagram_aligned"
SPLITS = ("train", "validation", "test")
PCA_COMPONENTS = [f"V{i}" for i in range(1, 29)]
SCALED_FEATURES = ["Time", "Amount", "hour_sin", "hour_cos", "V14_x_V17", "amount_log1p"]


class DiagramFeatures(BaseEstimator, TransformerMixin):
    """Construct the three feature types shown in the preprocessing diagram."""

    def fit(self, X: pd.DataFrame, y=None):
        self.transform(X)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        required = {"Time", "Amount", *PCA_COMPONENTS}
        missing = required.difference(X.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")
        result = X.loc[:, ["Time", "Amount", *PCA_COMPONENTS]].copy()
        if not np.isfinite(result.to_numpy(dtype=float)).all() or (result["Amount"] < 0).any():
            raise ValueError("Features must be finite and Amount must be nonnegative")
        angle = 2 * np.pi * (result["Time"].astype(float) % 86400) / 86400
        result["hour_sin"] = np.sin(angle)
        result["hour_cos"] = np.cos(angle)
        result["V14_x_V17"] = result["V14"] * result["V17"]
        result["amount_log1p"] = np.log1p(result["Amount"])
        return result


class DiagramScaler(BaseEstimator, TransformerMixin):
    """Scale the raw time/amount and the engineered features using training only."""

    def fit(self, X: pd.DataFrame, y=None):
        self.scaler_ = RobustScaler().fit(X[SCALED_FEATURES])
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        result = X.copy()
        result[SCALED_FEATURES] = self.scaler_.transform(result[SCALED_FEATURES])
        return result


def build_diagram_pipeline() -> Pipeline:
    return Pipeline([("features", DiagramFeatures()), ("scaler", DiagramScaler())])


def prepare_diagram_splits(splits: dict[str, pd.DataFrame]):
    if tuple(splits) != SPLITS:
        raise ValueError(f"Expected ordered splits: {SPLITS}")
    for name, frame in splits.items():
        if frame.empty or "Class" not in frame or not frame["Time"].is_monotonic_increasing:
            raise ValueError(f"{name} must be nonempty, labelled, and ordered by Time")
    for earlier, later in zip(SPLITS, SPLITS[1:]):
        if splits[earlier]["Time"].iloc[-1] >= splits[later]["Time"].iloc[0]:
            raise ValueError(f"{earlier} must end strictly before {later} begins")
    pipeline = build_diagram_pipeline().fit(splits["train"])
    transformed = {}
    for name, frame in splits.items():
        output = pipeline.transform(frame)
        output["Class"] = frame["Class"].to_numpy()
        transformed[name] = output
    return pipeline, transformed


def main() -> None:
    splits = {name: pd.read_parquet(INPUT / f"creditcard_{name}.parquet") for name in SPLITS}
    pipeline, transformed = prepare_diagram_splits(splits)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, frame in transformed.items():
        frame.to_parquet(OUTPUT / f"{name}.parquet", index=False)
    joblib.dump(pipeline, OUTPUT / "preprocessor.joblib")
    metadata = {
        "source": "existing deduplicated chronological splits in data/processed",
        "test_status": "previously exposed; not an untouched test set",
        "scaler_fit_split": "train",
        "scaled_features": SCALED_FEATURES,
        "engineered_features": ["hour_sin", "hour_cos", "V14_x_V17", "amount_log1p"],
        "rows": {name: len(frame) for name, frame in transformed.items()},
    }
    (OUTPUT / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved diagram-aligned data and preprocessor to {OUTPUT}")


if __name__ == "__main__":
    # Import by its stable package name so serialized transformers are reloadable.
    from src.fraud_detection.diagram_preprocessing import main as package_main

    package_main()
