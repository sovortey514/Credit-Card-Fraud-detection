import numpy as np
import pandas as pd
import pytest

from src.fraud_detection.preprocessing_pipeline import (
    RollingAmountHistory,
    build_creditcard_preprocessing_pipeline,
)
from src.fraud_detection.diagram_preprocessing import prepare_diagram_splits


def _split(times, amounts):
    rows = []
    for time, amount in zip(times, amounts):
        row = {"Time": time, "Amount": amount, "scaled_time": time, "scaled_amount": amount, "Class": 0}
        row.update({f"V{i}": float(i) for i in range(1, 29)})
        rows.append(row)
    return pd.DataFrame(rows)


def test_rejects_overlapping_chronological_splits():
    splits = {
        "train": _split([0, 10], [1, 2]),
        "validation": _split([10, 20], [3, 4]),
        "test": _split([30], [5]),
    }
    with pytest.raises(ValueError, match="train must end strictly before validation"):
        prepare_diagram_splits(splits)


def test_diagram_pipeline_uses_train_only_and_is_reusable(tmp_path):
    splits = {
        "train": _split([0, 21600, 43200], [1, 2, 3]),
        "validation": _split([64800], [100]),
        "test": _split([86400], [200]),
    }
    pipeline, outputs = prepare_diagram_splits(splits)
    assert pipeline.named_steps["scaler"].scaler_.center_[1] == pytest.approx(2)
    raw_features = pipeline.named_steps["features"].transform(splits["validation"])
    assert raw_features["hour_sin"].iloc[0] == pytest.approx(-1)
    assert raw_features["V14_x_V17"].iloc[0] == 14 * 17
    assert raw_features["amount_log1p"].iloc[0] == pytest.approx(np.log1p(100))
    pd.testing.assert_frame_equal(
        pipeline.transform(splits["test"]), outputs["test"].drop(columns="Class")
    )
    import joblib

    path = tmp_path / "preprocessor.joblib"
    joblib.dump(pipeline, path)
    pd.testing.assert_frame_equal(
        joblib.load(path).transform(splits["test"]), outputs["test"].drop(columns="Class")
    )


def test_batch_and_single_row_pipeline_outputs_match():
    frame = _split([0, 10, 20], [10, 20, 30]).drop(columns=["scaled_time", "scaled_amount", "Class"])
    pipeline = build_creditcard_preprocessing_pipeline().fit(frame)

    batch = pipeline.transform(frame)
    single = pipeline.transform(frame.iloc[[1]])

    pd.testing.assert_series_equal(
        batch.iloc[1][single.columns], single.iloc[0], check_names=False
    )


def test_rolling_history_is_chronological_and_resettable():
    history = RollingAmountHistory(window=2)
    first = history.transform_amount(10, 1)
    second = history.transform_amount(20, 2)
    assert first == pytest.approx((0.0, 1.0))
    assert second[0] == pytest.approx(10.0)
    assert second[1] == pytest.approx(1.0)
    with pytest.raises(ValueError, match="chronological"):
        history.transform_amount(30, 1)
    history.reset()
    assert history.transform_amount(10, 1) == pytest.approx(first)


def test_sequential_transform_uses_prior_history_and_current_percentile():
    frame = _split([1, 2, 3], [10, 20, 5]).drop(columns=["scaled_time", "scaled_amount", "Class"])
    pipeline = build_creditcard_preprocessing_pipeline().fit(frame)
    transformed = pipeline.named_steps["credit_card_features"].transform_sequential(frame)
    assert transformed["amount_rolling_percentile"].tolist() == pytest.approx([1.0, 1.0, 1 / 3])
    assert transformed["amount_rolling_zscore"].iloc[1] == pytest.approx(10.0)



    frame = _split(range(1_000), [float(i + 1) for i in range(1_000)]).drop(
        columns=["scaled_time", "scaled_amount", "Class"]
    )
    pipeline = build_creditcard_preprocessing_pipeline().fit(frame)
    import time

    started = time.perf_counter()
    pipeline.transform(frame)
    elapsed_ms_per_transaction = (time.perf_counter() - started) * 1_000 / len(frame)
    assert elapsed_ms_per_transaction < 2.0
