"""Load and serve the trained credit-card models and TreeSHAP explainers."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from app.schemas.creditcard import CreditCardTransaction, ExplanationResponse, PredictionResponse, SHAPContribution

import time
from uuid import uuid4

from app.services.prediction_history import PredictionHistoryRepository
from src.fraud_detection.preprocessing_pipeline import RollingAmountHistory

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "creditcard"
CALIBRATION_PATH = ROOT / "reports" / "models" / "creditcard_threshold_calibration_f1.json"
PREPROCESSING_PATH = ROOT / "models" / "creditcard_preprocessing.joblib"

MODEL_ARTIFACTS = {
    "xgboost": MODEL_DIR / "xgboost_class_weight_f1.joblib",
    "random_forest": MODEL_DIR / "random_forest_class_weight_f1.joblib",
}


def _class_one_values(explainer: shap.TreeExplainer, frame: pd.DataFrame) -> np.ndarray:
    values = explainer.shap_values(frame, check_additivity=False)
    if isinstance(values, list):
        return np.asarray(values[1] if len(values) > 1 else values[0])
    values = values.values if hasattr(values, "values") else np.asarray(values)
    return values[:, :, 1] if values.ndim == 3 else values


def _class_one_base_value(explainer: shap.TreeExplainer) -> float:
    value = np.asarray(explainer.expected_value).reshape(-1)
    return float(value[1] if len(value) > 1 else value[0])


class CreditCardModelService:
    """Application service that performs preprocessing, prediction, and explanation."""

    def __init__(self, history_repository: PredictionHistoryRepository | None = None) -> None:
        self.preprocessing = joblib.load(PREPROCESSING_PATH)
        self.history_repository = history_repository or PredictionHistoryRepository()
        self.models: dict[str, dict[str, object]] = {}
        self._histories: dict[str, RollingAmountHistory] = {}
        calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8")) if CALIBRATION_PATH.exists() else {"models": {}}
        for model_name, artifact_path in MODEL_ARTIFACTS.items():
            bundle = joblib.load(artifact_path)
            artifact_key = artifact_path.stem
            threshold = calibration.get("models", {}).get(artifact_key, {}).get("selected_threshold", 0.50)
            serialized_explainer = MODEL_DIR / f"{model_name}_treeshap_medoids50_f1.joblib"
            if serialized_explainer.exists():
                explain_bundle = joblib.load(serialized_explainer)
                explainer = explain_bundle["explainer"]
            else:
                explainer = shap.TreeExplainer(bundle["model"])
            self.models[model_name] = {
                "model": bundle["model"],
                "features": bundle["features"],
                "threshold": float(threshold),
                "explainer": explainer,
            }

    def reset_history(self, context_id: str = "default", initial_amounts: np.ndarray | None = None) -> None:
        """Reset one explicitly scoped chronological inference context."""
        if initial_amounts is None:
            transformer = self.preprocessing.named_steps["credit_card_features"]
            initial_amounts = getattr(transformer, "train_amounts_", np.asarray([], dtype=float))[-1_000:]
        self._histories[context_id] = RollingAmountHistory(
            window=getattr(self.preprocessing.named_steps["credit_card_features"], "rolling_window", 1_000),
            initial_amounts=initial_amounts,
        )

    def _history(self, context_id: str) -> RollingAmountHistory:
        if context_id not in self._histories:
            transformer = self.preprocessing.named_steps["credit_card_features"]
            self.reset_history(context_id, getattr(transformer, "train_amounts_", None)[-1_000:])
        return self._histories[context_id]

    def _features(
        self,
        transaction: CreditCardTransaction,
        model_name: str,
        context_id: str | None = None,
    ) -> pd.DataFrame:
        raw = transaction.to_frame()
        transformed = self.preprocessing.transform(raw)
        if context_id is not None:
            history = self._history(context_id)
            zscore, percentile = history.transform_amount(transaction.Amount, transaction.Time)
            transformed["amount_rolling_zscore"] = zscore
            transformed["amount_rolling_percentile"] = percentile
        features = self.models[model_name]["features"]
        return transformed[features]

    def predict(
        self,
        transaction: CreditCardTransaction,
        model_name: str,
        context_id: str | None = None,
    ) -> PredictionResponse:
        item = self.models[model_name]
        started = time.perf_counter()
        features = self._features(transaction, model_name, context_id)
        probability = float(item["model"].predict_proba(features)[0, 1])
        threshold = float(item["threshold"])
        try:
            self.history_repository.record(
                request_id=uuid4().hex,
                source="replay" if context_id and context_id.startswith("replay-") else "api",
                context_id=context_id,
                transaction_time=transaction.Time,
                amount=transaction.Amount,
                model=model_name,
                model_version=MODEL_ARTIFACTS[model_name].stem,
                feature_version="creditcard-f1-stateful-v1" if context_id else "creditcard-f1-reference-v1",
                probability=probability,
                threshold=threshold,
                is_fraud=probability >= threshold,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        except Exception:
            # Monitoring persistence is fail-open for this research prototype.
            pass
        return PredictionResponse(
            model=model_name,
            fraud_probability=probability,
            is_fraud=probability >= threshold,
            threshold=threshold,
        )

    def explain(self, transaction: CreditCardTransaction, model_name: str, top_n: int = 3, context_id: str | None = None) -> ExplanationResponse:
        item = self.models[model_name]
        features = self._features(transaction, model_name, context_id)
        probability = float(item["model"].predict_proba(features)[0, 1])
        threshold = float(item["threshold"])
        values = _class_one_values(item["explainer"], features)[0]
        ranking = pd.Series(values, index=features.columns).sort_values(key=np.abs, ascending=False).head(top_n)
        contributions = [
            SHAPContribution(
                feature=str(feature),
                value=float(value),
                direction="increases_risk" if value >= 0 else "decreases_risk",
            )
            for feature, value in ranking.items()
        ]
        return ExplanationResponse(
            model=model_name,
            fraud_probability=probability,
            is_fraud=probability >= threshold,
            threshold=threshold,
            base_value=_class_one_base_value(item["explainer"]),
            top_contributions=contributions,
        )
