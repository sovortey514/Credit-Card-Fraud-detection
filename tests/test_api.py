"""Integration tests for the credit-card fraud API."""

from fastapi.testclient import TestClient

from app.main import app


def _payload() -> dict[str, float]:
    return {"Time": 100.0, "Amount": 25.0, **{f"V{i}": float(i) for i in range(1, 29)}}


client = TestClient(app)


def test_predict_endpoint_returns_probability_and_decision():
    response = client.post("/api/v1/predict?model=xgboost", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "xgboost"
    assert 0 <= body["fraud_probability"] <= 1
    assert isinstance(body["is_fraud"], bool)
    assert 0 < body["threshold"] < 1


def test_explain_endpoint_returns_top_three_shap_contributions():
    response = client.post("/api/v1/explain?model=random_forest&top_n=3", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "random_forest"
    assert len(body["top_contributions"]) == 3
    assert all("feature" in item and "value" in item and "direction" in item for item in body["top_contributions"])


def test_payload_rejects_missing_pca_component():
    payload = _payload()
    del payload["V14"]
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 422
