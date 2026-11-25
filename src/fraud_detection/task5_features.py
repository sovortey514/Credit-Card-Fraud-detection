"""Build the Task 5 feature contract without altering historical models."""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from src.fraud_detection.engineer_creditcard_features import F0_FEATURES, SPLITS

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "processed"
OUTPUT = ROOT / "data" / "engineered_features"
EXTRA_FEATURES = ["hour_sin", "hour_cos", "amount_log1p", "amount_rolling_mean", "amount_rolling_std", "V14_x_V17", "V12_x_V10"]
F1_FEATURES = [*F0_FEATURES, *EXTRA_FEATURES]


def build_features(splits: dict[str, pd.DataFrame], window: int = 1000) -> dict[str, pd.DataFrame]:
    """Use previous rows only, carrying rolling history across split boundaries."""
    if tuple(splits) != SPLITS or window < 1:
        raise ValueError("Provide train, validation and test in order and a positive window")
    required = {"Time", "Amount", "Class", *F0_FEATURES}
    frames = []
    previous_end = None
    for name, frame in splits.items():
        if frame.empty or not required.issubset(frame.columns):
            raise ValueError(f"{name} is empty or missing required columns")
        if not frame["Time"].is_monotonic_increasing:
            raise ValueError(f"{name} must be sorted by Time")
        if previous_end is not None and frame["Time"].iloc[0] <= previous_end:
            raise ValueError("Split time ranges must be strictly ordered")
        previous_end = frame["Time"].iloc[-1]
        if (frame["Amount"] < 0).any() or not np.isfinite(frame["Amount"]).all():
            raise ValueError("Amount must be finite and non-negative")
        frames.append(frame.reset_index(drop=True).copy())
    all_rows = pd.concat(frames, ignore_index=True)
    prior = all_rows["Amount"].shift(1).rolling(window, min_periods=1)
    all_rows["amount_rolling_mean"] = prior.mean().fillna(0.0)
    all_rows["amount_rolling_std"] = prior.std(ddof=0).fillna(0.0)
    angle = 2 * np.pi * (all_rows["Time"] % 86400) / 86400
    all_rows["hour_sin"] = np.sin(angle)
    all_rows["hour_cos"] = np.cos(angle)
    all_rows["amount_log1p"] = np.log1p(all_rows["Amount"])
    all_rows["V14_x_V17"] = all_rows["V14"] * all_rows["V17"]
    all_rows["V12_x_V10"] = all_rows["V12"] * all_rows["V10"]
    outputs = {}
    start = 0
    for name, frame in zip(SPLITS, frames):
        outputs[name] = all_rows.iloc[start:start + len(frame)][["Time", *F1_FEATURES, "Class"]].reset_index(drop=True)
        start += len(frame)
    return outputs


def main() -> None:
    splits = {name: pd.read_parquet(SOURCE / f"creditcard_{name}.parquet") for name in SPLITS}
    outputs = build_features(splits)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        frame.to_parquet(OUTPUT / f"{name}.parquet", index=False)
    metadata = {"F0": F0_FEATURES, "F1": F1_FEATURES, "rolling_window_rows": 1000,
                "rolling_policy": "previous rows only; population std; zero when no history; stable input order for equal timestamps",
                "time_encoding": "24-hour phase relative to dataset start, not verified local hour",
                "scaling": "scaled_time and scaled_amount supplied by train-fitted preprocessing splits",
                "rows": {name: len(frame) for name, frame in outputs.items()}}
    (OUTPUT / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
