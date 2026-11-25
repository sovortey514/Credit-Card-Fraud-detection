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


def test_alert_status_and_review_survive_repository_reopen(tmp_path: Path):
    import sqlite3
    from datetime import datetime, timedelta, timezone

    path = tmp_path / "history.db"
    repository = PredictionHistoryRepository(path)
    repository.record(request_id="alert-1", source="replay", context_id="run-1", transaction_time=1,
                      amount=10, model="xgboost", model_version="v1", feature_version="v1",
                      probability=0.9, threshold=0.5, is_fraud=True, latency_ms=1)
    repository.record(request_id="clear-1", source="replay", context_id="run-1", transaction_time=2,
                      amount=10, model="xgboost", model_version="v1", feature_version="v1",
                      probability=0.1, threshold=0.5, is_fraud=False, latency_ms=1)
    assert [row['status'] for row in repository.alerts(300)] == ['pending']
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE prediction_history SET created_at = ? WHERE request_id = ?",
                           ((datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(), 'alert-1'))
    assert repository.alerts(300)[0]['status'] == 'overdue'
    repository.record_disposition('alert-1', 'APPROVED', 'analyst', 'Checked')
    alert = PredictionHistoryRepository(path).alerts(300)[0]
    assert (alert['status'], alert['disposition'], alert['notes']) == ('reviewed', 'APPROVED', 'Checked')
