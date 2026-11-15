import numpy as np
import pandas as pd
import pytest

from src.fraud_detection.engineer_creditcard_features import (
    F0_FEATURES,
    F1_FEATURES,
    engineer_split_features,
)
from src.fraud_detection.preprocessing_pipeline import build_creditcard_preprocessing_pipeline


def _split(times, amounts):
    rows = []
    for time, amount in zip(times, amounts):
        row = {"Time": time, "Amount": amount, "scaled_time": time, "scaled_amount": amount, "Class": 0}
        row.update({f"V{i}": float(i) for i in range(1, 29)})
        rows.append(row)
    return pd.DataFrame(rows)


def test_creditcard_features_are_chronological_and_leakage_safe():
    splits = {
        "train": _split([0, 10, 20], [1, 2, 3]),
        "validation": _split([30, 40], [4, 5]),
        "test": _split([50, 60], [6, 7]),
    }
    result = engineer_split_features(splits)

    assert list(result["train"].columns[: len(F0_FEATURES) + 1]) == ["Time", *F0_FEATURES]
    assert set(F1_FEATURES).issubset(result["test"].columns)
    assert result["validation"].iloc[0]["amount_rolling_zscore"] == pytest.approx(
        2.449489742783178
    )
    assert result["test"].iloc[0]["amount_global_percentile"] == 1.0
    assert result["train"]["Time"].is_monotonic_increasing
    assert np.isfinite(result["test"].select_dtypes("number")).all().all()


def test_interactions_cover_top_components():
    splits = {name: _split([i], [10 + i]) for i, name in enumerate(("train", "validation", "test"))}
    result = engineer_split_features(splits)
    assert "V14_x_V17" in result["train"]
    assert "V12_x_V10" in result["train"]


def test_batch_and_single_row_pipeline_outputs_match():
    frame = _split([0, 10, 20], [10, 20, 30]).drop(columns=["scaled_time", "scaled_amount", "Class"])
    pipeline = build_creditcard_preprocessing_pipeline().fit(frame)

    batch = pipeline.transform(frame)
    single = pipeline.transform(frame.iloc[[1]])

    pd.testing.assert_series_equal(
        batch.iloc[1][single.columns], single.iloc[0], check_names=False
    )


def test_pipeline_transform_latency_is_below_two_ms_per_transaction():
    frame = _split(range(1_000), [float(i + 1) for i in range(1_000)]).drop(
        columns=["scaled_time", "scaled_amount", "Class"]
    )
    pipeline = build_creditcard_preprocessing_pipeline().fit(frame)
    import time

    started = time.perf_counter()
    pipeline.transform(frame)
    elapsed_ms_per_transaction = (time.perf_counter() - started) * 1_000 / len(frame)
    assert elapsed_ms_per_transaction < 2.0
