"""Feature engineering helpers for the Credit Card and PaySim datasets."""

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


def engineer_features_paysim(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer features for the PaySim synthetic dataset."""
    required = {
        "type",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing PaySim columns: {sorted(missing)}")

    result = df.copy()
    result["errorBalanceOrig"] = (
        result["newbalanceOrig"] + result["amount"] - result["oldbalanceOrg"]
    )
    result["errorBalanceDest"] = (
        result["oldbalanceDest"] + result["amount"] - result["newbalanceDest"]
    )
    result["amount_to_orig_balance_ratio"] = result["amount"] / (
        result["oldbalanceOrg"] + 1e-5
    )
    result["is_orig_zero_after"] = (result["newbalanceOrig"] == 0).astype(int)
    result["is_dest_zero_before"] = (result["oldbalanceDest"] == 0).astype(int)
    result = pd.get_dummies(result, columns=["type"], drop_first=True)

    print(f"Engineered PaySim features. New total columns: {result.shape[1]}")
    return result
