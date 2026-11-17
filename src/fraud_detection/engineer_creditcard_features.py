"""Build leakage-safe F0/F1 features from chronological credit-card splits."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
SPLITS = ("train", "validation", "test")
ROLLING_WINDOW = 1_000
PCA_COMPONENTS = [f"V{i}" for i in range(1, 29)]
INTERACTION_COMPONENTS = ["V14", "V17", "V12", "V10"]

F0_FEATURES = ["scaled_time", "scaled_amount", *PCA_COMPONENTS]
F1_FEATURES = [
    "hour_sin",
    "hour_cos",
    "amount_log1p",
    "amount_global_zscore",
    "amount_global_percentile",
    "amount_rolling_zscore",
    "amount_rolling_percentile",
]


def _require_columns(frame: pd.DataFrame) -> None:
    required = {"Time", "Amount", "scaled_time", "scaled_amount", "Class", *PCA_COMPONENTS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required credit-card columns: {missing}")


def _global_percentile(amount: pd.Series, train_amount: np.ndarray) -> np.ndarray:
    """Return each value's empirical percentile against the train distribution."""
    ordered = np.sort(train_amount)
    return np.searchsorted(ordered, amount.to_numpy(), side="right") / len(ordered)


def _add_amount_features(frame: pd.DataFrame, train_amount: np.ndarray) -> None:
    amount = frame["Amount"].astype(float)
    train_mean = float(train_amount.mean())
    train_std = float(train_amount.std(ddof=0))
    if train_std == 0:
        train_std = 1.0

    frame["amount_global_zscore"] = (amount - train_mean) / train_std
    frame["amount_global_percentile"] = _global_percentile(amount, train_amount)

    history = amount.shift(1)
    rolling_mean = history.rolling(ROLLING_WINDOW, min_periods=1).mean()
    rolling_std = history.rolling(ROLLING_WINDOW, min_periods=2).std(ddof=0)
    frame["amount_rolling_zscore"] = ((amount - rolling_mean) / rolling_std.replace(0, np.nan))
    frame["amount_rolling_zscore"] = frame["amount_rolling_zscore"].fillna(
        frame["amount_global_zscore"]
    )

    # The current amount is compared with itself and prior rows only. No future
    # row can enter this window; the first row therefore has percentile 1.0.
    frame["amount_rolling_percentile"] = (
        amount.rolling(ROLLING_WINDOW, min_periods=1).rank(pct=True).astype(float)
    )


def engineer_split_features(splits: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Create F0/F1 features while preserving the existing chronological order."""
    if tuple(splits) != SPLITS:
        raise ValueError(f"Splits must be provided in chronological order: {SPLITS}")
    for frame in splits.values():
        _require_columns(frame)
        if frame.empty:
            raise ValueError("Chronological splits must not be empty")
        if not frame["Time"].is_monotonic_increasing:
            raise ValueError("Each split must be sorted by Time before feature engineering")

    for earlier, later in zip(SPLITS, SPLITS[1:]):
        if splits[earlier]["Time"].iloc[-1] >= splits[later]["Time"].iloc[0]:
            raise ValueError(f"{earlier} must end strictly before {later} begins")

    train_amount = splits["train"]["Amount"].astype(float).to_numpy()
    result: dict[str, pd.DataFrame] = {}
    previous_amount = pd.Series(dtype=float)
    for name in SPLITS:
        frame = splits[name].copy()
        # Carry prior split history into validation/test rolling calculations.
        history_frame = pd.concat(
            [previous_amount, frame["Amount"].astype(float)], ignore_index=True
        )
        engineered_history = pd.DataFrame({"Amount": history_frame})
        _add_amount_features(engineered_history, train_amount)

        time_seconds = frame["Time"].astype(float)
        hour_angle = 2 * np.pi * ((time_seconds % 86_400) / 86_400)
        frame["hour_sin"] = np.sin(hour_angle)
        frame["hour_cos"] = np.cos(hour_angle)
        frame["amount_log1p"] = np.log1p(frame["Amount"].astype(float))
        for column in F1_FEATURES[3:]:
            frame[column] = engineered_history[column].iloc[-len(frame) :].to_numpy()

        for left_index, left in enumerate(INTERACTION_COMPONENTS):
            for right in INTERACTION_COMPONENTS[left_index + 1 :]:
                frame[f"{left}_x_{right}"] = frame[left] * frame[right]

        result[name] = frame[["Time", *F0_FEATURES, *F1_FEATURES,
                              *[f"{left}_x_{right}" for i, left in enumerate(INTERACTION_COMPONENTS)
                                for right in INTERACTION_COMPONENTS[i + 1 :]], "Class"]]
        previous_amount = history_frame
    return result


def main() -> None:
    splits = {
        name: pd.read_parquet(PROCESSED / f"creditcard_{name}.parquet") for name in SPLITS
    }
    engineered = engineer_split_features(splits)
    for name, frame in engineered.items():
        frame.to_parquet(PROCESSED / f"creditcard_{name}_features.parquet", index=False)

    metadata = {
        "feature_sets": {"F0": F0_FEATURES, "F1": F1_FEATURES},
        "interaction_components": INTERACTION_COMPONENTS,
        "interaction_features": [
            column for column in engineered["train"].columns if "_x_" in column
        ],
        "rolling_window_rows": ROLLING_WINDOW,
        "global_statistics_fit_split": "train",
        "scaling": "Time and Amount scaled in the input splits using train-fitted RobustScalers; engineered features are not robust-scaled",
        "inference_rolling_features_match": False,
        "inference_rolling_features_note": "Offline features use evolving transaction history; the inference pipeline uses a fixed training reference. Models using these features require aligned preprocessing and retraining.",
        "rolling_order": "chronological; each row uses prior rows only for z-score and current-or-prior rows for percentile rank",
        "future_to_past_leakage": False,
        "rows": {name: len(frame) for name, frame in engineered.items()},
    }
    (PROCESSED / "creditcard_feature_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
