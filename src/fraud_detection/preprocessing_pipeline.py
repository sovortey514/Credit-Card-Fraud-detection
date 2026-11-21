"""Reusable, train-fitted preprocessing for credit-card fraud inference."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler


ROOT = Path(__file__).resolve().parents[2]
PCA_COMPONENTS = [f"V{i}" for i in range(1, 29)]
INTERACTION_COMPONENTS = ["V14", "V17", "V12", "V10"]
RAW_FEATURES = ["Time", "Amount", *PCA_COMPONENTS]
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
INTERACTION_FEATURES = [
    f"{left}_x_{right}"
    for left_index, left in enumerate(INTERACTION_COMPONENTS)
    for right in INTERACTION_COMPONENTS[left_index + 1 :]
]


def _validate_input(frame: pd.DataFrame) -> None:
    missing = sorted(set(RAW_FEATURES) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing credit-card columns: {missing}")
    if frame.empty:
        raise ValueError("At least one transaction is required")


class RollingAmountHistory:
    """Bounded chronological state matching the offline rolling features."""

    def __init__(self, window: int = 1_000, initial_amounts: np.ndarray | None = None) -> None:
        if window < 1:
            raise ValueError("rolling window must be positive")
        self.window = int(window)
        self._values: deque[float] = deque(maxlen=self.window)
        self.last_time: float | None = None
        if initial_amounts is not None:
            for amount in np.asarray(initial_amounts, dtype=float)[-self.window :]:
                self._values.append(float(amount))

    def reset(self) -> None:
        self._values.clear()
        self.last_time = None

    def transform_amount(self, amount: float, time: float | None = None) -> tuple[float, float]:
        """Return z-score and current-or-prior percentile, then append the row."""
        amount = float(amount)
        if not np.isfinite(amount):
            raise ValueError("Amount must be finite")
        if time is not None:
            time = float(time)
            if self.last_time is not None and time < self.last_time:
                raise ValueError("Transactions must be processed in chronological order")

        prior = np.asarray(self._values, dtype=float)
        if prior.size:
            mean = float(prior.mean())
            std = float(prior.std(ddof=0))
            zscore = (amount - mean) / (std if std else 1.0)
        else:
            zscore = 0.0

        current = np.concatenate([prior, np.asarray([amount])])
        percentile = float((current <= amount).sum() / current.size)
        self._values.append(amount)
        self.last_time = time
        return zscore, percentile

    @property
    def values(self) -> tuple[float, ...]:
        return tuple(self._values)


class CreditCardFeatureTransformer(BaseEstimator, TransformerMixin):
    """Fit preprocessing statistics on training data and transform transactions.

    Incoming rows are scored independently against the fitted training history.
    This keeps single-row API inference identical to batch inference and prevents
    a later row in a request batch from influencing an earlier row.
    """

    def __init__(self, rolling_window: int = 1_000) -> None:
        self.rolling_window = rolling_window

    def fit(self, X: pd.DataFrame, y=None):
        _validate_input(X)
        train = X.sort_values("Time", kind="stable")
        self.amount_scaler_ = RobustScaler().fit(train[["Amount"]])
        self.time_scaler_ = RobustScaler().fit(train[["Time"]])

        amounts = train["Amount"].astype(float).to_numpy()
        self.train_amounts_ = np.sort(amounts)
        self.train_amount_mean_ = float(amounts.mean())
        self.train_amount_std_ = float(amounts.std(ddof=0)) or 1.0
        history = amounts[-self.rolling_window :]
        self.rolling_amount_mean_ = float(history.mean())
        self.rolling_amount_std_ = float(history.std(ddof=0)) or 1.0
        self.n_features_in_ = len(RAW_FEATURES)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if not hasattr(self, "train_amounts_"):
            raise RuntimeError("CreditCardFeatureTransformer must be fitted first")
        _validate_input(X)
        result = X.copy()
        time = result["Time"].astype(float)
        amount = result["Amount"].astype(float)

        result["scaled_amount"] = self.amount_scaler_.transform(result[["Amount"]]).ravel()
        result["scaled_time"] = self.time_scaler_.transform(result[["Time"]]).ravel()
        result["hour_of_day"] = (time / 3600) % 24
        result["is_night_transaction"] = ((result["hour_of_day"] >= 22) | (result["hour_of_day"] <= 5)).astype(int)
        result["log_amount"] = np.log1p(amount)

        hour_angle = 2 * np.pi * ((time % 86_400) / 86_400)
        result["hour_sin"] = np.sin(hour_angle)
        result["hour_cos"] = np.cos(hour_angle)
        result["amount_log1p"] = np.log1p(amount)
        result["amount_global_zscore"] = (amount - self.train_amount_mean_) / self.train_amount_std_
        result["amount_global_percentile"] = (
            np.searchsorted(self.train_amounts_, amount.to_numpy(), side="right")
            / len(self.train_amounts_)
        )
        result["amount_rolling_zscore"] = (
            amount - self.rolling_amount_mean_
        ) / self.rolling_amount_std_
        result["amount_rolling_percentile"] = (
            np.searchsorted(self.train_amounts_[-self.rolling_window :], amount.to_numpy(), side="right")
            / self.rolling_window
        )

        for left_index, left in enumerate(INTERACTION_COMPONENTS):
            for right in INTERACTION_COMPONENTS[left_index + 1 :]:
                result[f"{left}_x_{right}"] = result[left].astype(float) * result[right].astype(float)

        return result
    def transform_sequential(
        self,
        X: pd.DataFrame,
        initial_amounts: np.ndarray | None = None,
    ) -> pd.DataFrame:
        """Transform chronological rows using explicit evolving amount history."""
        if not hasattr(self, "train_amounts_"):
            raise RuntimeError("CreditCardFeatureTransformer must be fitted first")
        _validate_input(X)
        result = self.transform(X)
        history = RollingAmountHistory(self.rolling_window, initial_amounts)
        rolling_zscores: list[float] = []
        rolling_percentiles: list[float] = []
        for row in X.sort_values("Time", kind="stable").itertuples(index=False):
            zscore, percentile = history.transform_amount(row.Amount, row.Time)
            if not history.values[:-1]:
                zscore = float((float(row.Amount) - self.train_amount_mean_) / self.train_amount_std_)
            rolling_zscores.append(zscore)
            rolling_percentiles.append(percentile)
        ordered = X.sort_values("Time", kind="stable").index
        sequential = result.loc[ordered].copy()
        sequential["amount_rolling_zscore"] = rolling_zscores
        sequential["amount_rolling_percentile"] = rolling_percentiles
        return sequential.loc[X.index]



def build_creditcard_preprocessing_pipeline() -> Pipeline:
    """Return the sklearn pipeline used by training and API inference."""
    return Pipeline([("credit_card_features", CreditCardFeatureTransformer())])
