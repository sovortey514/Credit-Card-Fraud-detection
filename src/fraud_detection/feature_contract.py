"""F0/F1 preprocessing with explicit, caller-owned chronological history."""
from collections import deque
import math

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.utils.validation import check_is_fitted

from src.fraud_detection.task5_features import F0_FEATURES, F1_FEATURES


class FeatureContract(BaseEstimator, TransformerMixin):
    def __init__(self, feature_set="F1", window=1000):
        self.feature_set = feature_set
        self.window = window

    def fit(self, X, y=None):
        if self.feature_set not in ("F0", "F1") or self.window < 1:
            raise ValueError("Invalid feature set or rolling window")
        self.scaler_ = RobustScaler().fit(X[["Time", "Amount"]])
        return self

    def transform(self, X):
        """Transform a chronological batch starting with empty history."""
        return self.transform_with_history(X)[0]

    def transform_one(self, transaction, history=None, last_time=None):
        """Transform a validated API mapping and return explicit updated history."""
        check_is_fitted(self, "scaler_")
        time, amount = float(transaction["Time"]), float(transaction["Amount"])
        if not math.isfinite(time) or not math.isfinite(amount) or amount < 0:
            raise ValueError("Time and non-negative Amount must be finite")
        if last_time is not None and time < last_time:
            raise ValueError("Transaction precedes supplied history")
        previous = list(history if history is not None else [])[-self.window:]
        if any(not math.isfinite(value) or value < 0 for value in previous):
            raise ValueError("History must contain finite non-negative amounts")
        center, scale = self.scaler_.center_, self.scaler_.scale_
        features = {"scaled_time": (time - center[0]) / scale[0],
                    "scaled_amount": (amount - center[1]) / scale[1]}
        features.update({f"V{i}": float(transaction[f"V{i}"]) for i in range(1, 29)})
        if not all(math.isfinite(value) for value in features.values()):
            raise ValueError("Features must be finite")
        if self.feature_set == "F1":
            mean = sum(previous) / len(previous) if previous else 0.0
            std = math.sqrt(sum((value - mean) ** 2 for value in previous) / len(previous)) if previous else 0.0
            angle = 2 * math.pi * (time % 86400) / 86400
            features.update(hour_sin=math.sin(angle), hour_cos=math.cos(angle), amount_log1p=math.log1p(amount),
                            amount_rolling_mean=mean, amount_rolling_std=std,
                            V14_x_V17=features["V14"] * features["V17"], V12_x_V10=features["V12"] * features["V10"])
        return features, (previous + [amount])[-self.window:], time

    def transform_with_history(self, X, history=None, last_time=None):
        """Return features, bounded history and last timestamp for the next batch."""
        check_is_fitted(self, "scaler_")
        if X.empty or not X["Time"].is_monotonic_increasing:
            raise ValueError("Rows must be nonempty and ordered by Time")
        if last_time is not None and X["Time"].iloc[0] < last_time:
            raise ValueError("Batch precedes supplied history")
        amounts = X["Amount"].to_numpy(dtype=float)
        if not np.isfinite(amounts).all() or (amounts < 0).any():
            raise ValueError("Amounts must be finite and non-negative")
        scaled = self.scaler_.transform(X[["Time", "Amount"]])
        result = X[[f"V{i}" for i in range(1, 29)]].copy()
        result["scaled_time"], result["scaled_amount"] = scaled[:, 0], scaled[:, 1]
        previous = list(history if history is not None else [])[-self.window:]
        if self.feature_set == "F0":
            return result[F0_FEATURES], list(deque(previous + amounts.tolist(), maxlen=self.window)), float(X["Time"].iloc[-1])
        combined = pd.Series(previous + amounts.tolist(), dtype=float)
        rolling = combined.shift(1).rolling(self.window, min_periods=1)
        result["amount_rolling_mean"] = rolling.mean().fillna(0).iloc[len(previous):].to_numpy()
        result["amount_rolling_std"] = rolling.std(ddof=0).fillna(0).iloc[len(previous):].to_numpy()
        angle = 2 * np.pi * (X["Time"].to_numpy(dtype=float) % 86400) / 86400
        result["hour_sin"], result["hour_cos"] = np.sin(angle), np.cos(angle)
        result["amount_log1p"] = np.log1p(amounts)
        result["V14_x_V17"] = X["V14"] * X["V17"]
        result["V12_x_V10"] = X["V12"] * X["V10"]
        return result[F1_FEATURES], list(deque(previous + amounts.tolist(), maxlen=self.window)), float(X["Time"].iloc[-1])


def build_feature_pipeline(feature_set="F1", window=1000):
    return Pipeline([("features", FeatureContract(feature_set, window))])
