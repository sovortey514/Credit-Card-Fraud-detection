from pathlib import Path

from app.services.prediction_history import PredictionHistoryRepository


def test_prediction_history_records_metadata_without_raw_payload(tmp_path: Path):
    repository = PredictionHistoryRepository(tmp_path / "history.db")
    prediction_id = repository.record(
        request_id="request-1",
        source="api",
        context_id=None,
        transaction_time=12.0,
        amount=99.5,
        model="xgboost",
        model_version="model-v1",
        feature_version="features-v1",
        probability=0.8,
        threshold=0.5,
        is_fraud=True,
        latency_ms=2.5,
    )
    assert prediction_id == 1
    row = repository.recent(1)[0]
    assert row["model"] == "xgboost"
    assert row["is_fraud"] == 1
    assert "V1" not in row
    assert repository.summary() == {
        "total_predictions": 1,
        "fraud_alerts": 1,
        "alert_rate": 1.0,
        "average_latency_ms": 2.5,
        "p95_latency_ms": 2.5,
    }
