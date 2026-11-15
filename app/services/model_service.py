"""Load and serve the trained credit-card models and TreeSHAP explainers."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from app.schemas.creditcard import CreditCardTransaction, ExplanationResponse, PredictionResponse, SHAPContribution

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

    def __init__(self) -> None:
        self.preprocessing = joblib.load(PREPROCESSING_PATH)
        self.models: dict[str, dict[str, object]] = {}
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

    def _features(self, transaction: CreditCardTransaction, model_name: str) -> pd.DataFrame:
        raw = transaction.to_frame()
        transformed = self.preprocessing.transform(raw)
        features = self.models[model_name]["features"]
        return transformed[features]

    def predict(self, transaction: CreditCardTransaction, model_name: str) -> PredictionResponse:
        item = self.models[model_name]
        features = self._features(transaction, model_name)
        probability = float(item["model"].predict_proba(features)[0, 1])
        threshold = float(item["threshold"])
        return PredictionResponse(
            model=model_name,
            fraud_probability=probability,
            is_fraud=probability >= threshold,
            threshold=threshold,
        )

    def explain(self, transaction: CreditCardTransaction, model_name: str, top_n: int = 3) -> ExplanationResponse:
        item = self.models[model_name]
        features = self._features(transaction, model_name)
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
