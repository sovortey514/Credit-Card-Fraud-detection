import numpy as np
import pandas as pd
import pytest

from src.fraud_detection.task5_features import F0_FEATURES, F1_FEATURES, build_features


def make_frame(times, amounts):
    frame = pd.DataFrame({"Time": times, "Amount": amounts, "scaled_time": times, "scaled_amount": amounts, "Class": 0})
    for i in range(1, 29):
        frame[f"V{i}"] = float(i)
    return frame


def test_feature_contract_and_strict_history():
    splits = {"train": make_frame([0, 21600], [10, 20]), "validation": make_frame([43200], [30]), "test": make_frame([64800], [40])}
    result = build_features(splits, window=2)
    assert len(F0_FEATURES) == 30 and len(F1_FEATURES) == 37
    assert result["train"]["amount_rolling_mean"].tolist() == [0, 10]
    assert result["validation"]["amount_rolling_mean"].iloc[0] == 15
    assert result["test"]["amount_rolling_mean"].iloc[0] == 25
    assert result["validation"]["amount_rolling_std"].iloc[0] == 5
    assert result["train"]["hour_sin"].iloc[1] == pytest.approx(1)
    assert result["test"]["amount_log1p"].iloc[0] == pytest.approx(np.log1p(40))
    assert result["test"]["V14_x_V17"].iloc[0] == 14 * 17
    assert result["test"]["V12_x_V10"].iloc[0] == 12 * 10
    changed = {key: value.copy() for key, value in splits.items()}
    changed["test"].loc[0, "Amount"] = 4000
    assert build_features(changed, window=2)["test"]["amount_rolling_mean"].iloc[0] == 25
