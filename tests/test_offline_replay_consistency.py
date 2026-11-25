"""Compare saved offline features and scores with chronological replay inference."""

import pandas as pd
import pytest

from app.services.model_service import CreditCardModelService, MODEL_ARTIFACTS
from app.services.replay_service import CreditCardReplayService, ROOT, TEST_PATH


@pytest.mark.parametrize("model_name", ["random_forest", "xgboost"])
def test_replay_matches_offline_model_scores(model_name, monkeypatch):
    feature_path = ROOT / "data/processed/creditcard_test_features.parquet"
    required = [TEST_PATH, feature_path, *MODEL_ARTIFACTS.values(), ROOT / "models/creditcard_preprocessing.joblib"]
    if not all(path.exists() for path in required):
        pytest.skip("Research data or saved model artifacts are unavailable")

    service = CreditCardModelService()
    replay = CreditCardReplayService(service)
    monkeypatch.setattr(service, "_contributions", lambda *args: [])
    monkeypatch.setattr(service.history_repository, "record", lambda **kwargs: None)
    context = f"consistency-{model_name}"
    service.reset_history(context, replay.initial_history().to_numpy())
    offline = pd.read_parquet(feature_path).head(30)
    bundle = service.models[model_name]
    expected = bundle["model"].predict_proba(offline[bundle["features"]])[:, 1]
    threshold = bundle["threshold"]

    for index, transaction in enumerate(replay.transactions(limit=len(offline))):
        event = replay.score(transaction, index, model_name, context)
        assert event.ml_probability == pytest.approx(expected[index], abs=1e-7)
        # Rules may flag a transaction whose ML score is below threshold.
        if expected[index] >= threshold:
            assert event.route == "flag"
        if event.route == "flag" and expected[index] < threshold:
            assert any(rule["severity"] == "high" for rule in event.triggered_rules)
