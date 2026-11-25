import joblib
import numpy as np
import pandas as pd
import pytest
from src.fraud_detection.feature_contract import build_feature_pipeline
from src.fraud_detection.task5_features import build_features
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import feature_contract as api


@pytest.mark.parametrize("feature_set", ["F0", "F1"])
def test_serialized_pipeline_matches_single_row_and_offline(feature_set, tmp_path):
    frame = pd.DataFrame({"Time": [0., 1., 2., 3.], "Amount": [10., 20., 5., 40.]})
    for i in range(1, 29):
        frame[f"V{i}"] = float(i)
    pipeline = build_feature_pipeline(feature_set, window=2).fit(frame.iloc[:2])
    path = tmp_path / "pipeline.joblib"
    joblib.dump(pipeline, path)
    pipeline = joblib.load(path)
    batch = pipeline.transform(frame)
    history, last_time, rows = [], None, []
    transformer = pipeline.named_steps["features"]
    for i in range(len(frame)):
        row, history, last_time = transformer.transform_with_history(frame.iloc[i:i+1], history, last_time)
        rows.append(row)
    pd.testing.assert_frame_equal(batch, pd.concat(rows))
    scaled = transformer.scaler_.transform(frame[["Time", "Amount"]])
    source = frame.assign(scaled_time=scaled[:, 0], scaled_amount=scaled[:, 1], Class=0)
    offline = build_features({"train": source.iloc[:2], "validation": source.iloc[2:3], "test": source.iloc[3:]}, window=2)
    expected = pd.concat(offline.values(), ignore_index=True)[batch.columns]
    np.testing.assert_allclose(batch.to_numpy(), expected.to_numpy())


@pytest.mark.parametrize("feature_set", ["F0", "F1"])
def test_api_matches_batch_with_explicit_history(feature_set, monkeypatch):
    frame = pd.DataFrame({"Time": [0., 1., 2., 3.], "Amount": [10., 20., 5., 40.]})
    for i in range(1, 29):
        frame[f"V{i}"] = float(i)
    pipeline = build_feature_pipeline(feature_set, window=2).fit(frame.iloc[:2])
    monkeypatch.setattr(api, "load_transformer", lambda _: pipeline.named_steps["features"])
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    history, last_time, actual = [], None, []
    for transaction in frame.to_dict(orient="records"):
        response = client.post("/api/v1/features", json={"transaction": transaction, "feature_set": feature_set, "history": history, "last_time": last_time})
        assert response.status_code == 200, response.text
        result = response.json()
        actual.append(result["features"])
        history, last_time = result["history"], result["last_time"]
    expected = pipeline.transform(frame)
    np.testing.assert_allclose(pd.DataFrame(actual)[expected.columns].to_numpy(), expected.to_numpy(), rtol=1e-10, atol=1e-10)
