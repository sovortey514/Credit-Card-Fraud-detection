"""Feature engineering helpers for credit-card fraud detection."""

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler


def engineer_features_creditcard(
    df: pd.DataFrame,
    *,
    amount_scaler: RobustScaler | None = None,
    time_scaler: RobustScaler | None = None,
) -> pd.DataFrame:
    """Engineer features for the standard Credit Card Fraud dataset."""
    required = {"Amount", "Time"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing Credit Card columns: {sorted(missing)}")

    result = df.copy()
    amount_scaler = amount_scaler or RobustScaler().fit(result[["Amount"]])
    time_scaler = time_scaler or RobustScaler().fit(result[["Time"]])
    result["scaled_amount"] = amount_scaler.transform(result[["Amount"]]).ravel()
    result["scaled_time"] = time_scaler.transform(result[["Time"]]).ravel()
    result["hour_of_day"] = (result["Time"] / 3600) % 24
    result["is_night_transaction"] = (
        (result["hour_of_day"] >= 22) | (result["hour_of_day"] <= 5)
    ).astype(int)
    result["log_amount"] = np.log1p(result["Amount"])

    print(f"Engineered Credit Card features. New total columns: {result.shape[1]}")
    return result


