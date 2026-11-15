"""Generate global and local TreeSHAP explanations for final card-fraud models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "models" / "creditcard"
REPORT_DIR = ROOT / "reports" / "explainability"
CALIBRATION_PATH = ROOT / "reports" / "models" / "creditcard_threshold_calibration_f1.json"
TARGET = "Class"
SEED = 42
MODEL_ARTIFACTS = {
    "random_forest": "random_forest_class_weight_f1.joblib",
    "xgboost": "xgboost_class_weight_f1.joblib",
}


def class_one_shap_values(explainer: shap.TreeExplainer, X: pd.DataFrame) -> np.ndarray:
    """Return SHAP values for the fraud class across SHAP API versions."""
    result = explainer.shap_values(X, check_additivity=False)
    if isinstance(result, list):
        return np.asarray(result[1] if len(result) > 1 else result[0])
    values = result.values if hasattr(result, "values") else np.asarray(result)
    if values.ndim == 3:
        return values[:, :, 1]
    return values


def expected_value_for_class_one(explainer: shap.TreeExplainer) -> float:
    value = explainer.expected_value
    if isinstance(value, (list, np.ndarray)):
        array = np.asarray(value).reshape(-1)
        return float(array[1] if len(array) > 1 else array[0])
    return float(value)


def local_waterfall(
    explanation: shap.Explanation,
    row_index: int,
    label: str,
    model_name: str,
) -> str:
    figure = plt.figure(figsize=(10, 7))
    shap.plots.waterfall(explanation[row_index], max_display=15, show=False)
    figure = plt.gcf()
    figure.suptitle(f"{model_name}: validation {label}", y=0.98)
    output = REPORT_DIR / f"{model_name}_validation_{label.lower().replace(' ', '_')}_waterfall.png"
    figure.tight_layout()
    figure.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return str(output.relative_to(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-set", choices=("F0", "F1"), default="F1")
    args = parser.parse_args()

    validation = pd.read_parquet(DATA_DIR / "creditcard_validation_features.parquet")
    y_validation = validation[TARGET].astype(int)
    calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8")) if CALIBRATION_PATH.exists() else {"models": {}}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict[str, object] = {
        "dataset": "Kaggle ULB Credit Card Fraud Detection",
        "feature_set": args.feature_set,
        "split": "validation",
        "validation_rows": len(validation),
        "seed": SEED,
        "tree_shap": True,
        "models": {},
    }

    for model_name, artifact_name in MODEL_ARTIFACTS.items():
        artifact_path = MODEL_DIR / artifact_name
        if not artifact_path.exists():
            summary["models"][model_name] = {"status": "missing", "artifact": str(artifact_path.relative_to(ROOT))}
            continue

        bundle = joblib.load(artifact_path)
        model = bundle["model"]
        features = bundle["features"]
        X_validation = validation[features]
        probabilities = model.predict_proba(X_validation)[:, 1]
        artifact_key = artifact_path.stem
        threshold = calibration.get("models", {}).get(artifact_key, {}).get("selected_threshold", 0.50)
        predictions = probabilities >= threshold
        explainer = shap.TreeExplainer(model)
        values = class_one_shap_values(explainer, X_validation)
        base_value = expected_value_for_class_one(explainer)
        explanation = shap.Explanation(
            values=values,
            base_values=np.full(len(X_validation), base_value),
            data=X_validation.to_numpy(),
            feature_names=list(features),
        )

        mean_abs = np.abs(values).mean(axis=0)
        importance = pd.DataFrame({"feature": features, "mean_abs_shap": mean_abs}).sort_values(
            "mean_abs_shap", ascending=False
        )
        importance.to_csv(REPORT_DIR / f"{model_name}_validation_mean_abs_shap.csv", index=False)

        top = importance.head(20).sort_values("mean_abs_shap")
        figure, axis = plt.subplots(figsize=(10, 8))
        axis.barh(top["feature"], top["mean_abs_shap"], color="#2b7a78")
        axis.set(title=f"{model_name}: mean(|TreeSHAP|) on validation", xlabel="Mean absolute SHAP value")
        figure.tight_layout()
        mean_plot = REPORT_DIR / f"{model_name}_validation_mean_abs_shap.png"
        figure.savefig(mean_plot, dpi=160)
        plt.close(figure)

        shap.summary_plot(values, X_validation, feature_names=features, max_display=20, show=False)
        figure = plt.gcf()
        figure.tight_layout()
        beeswarm_plot = REPORT_DIR / f"{model_name}_validation_shap_beeswarm.png"
        figure.savefig(beeswarm_plot, dpi=160, bbox_inches="tight")
        plt.close(figure)

        true_positive_indices = np.flatnonzero((y_validation.to_numpy() == 1) & predictions)
        false_positive_indices = np.flatnonzero((y_validation.to_numpy() == 0) & predictions)
        local: dict[str, object] = {}
        for label, indices in (("true_positive", true_positive_indices), ("false_positive", false_positive_indices)):
            if len(indices) == 0:
                local[label] = {"status": "no_validation_examples_at_selected_threshold"}
                continue
            selected_index = int(indices[np.argmax(probabilities[indices])])
            local[label] = {
                "row_index": selected_index,
                "probability": float(probabilities[selected_index]),
                "threshold": float(threshold),
                "waterfall_plot": local_waterfall(explanation, selected_index, label.replace("_", " "), model_name),
            }

        summary["models"][model_name] = {
            "status": "complete",
            "artifact": str(artifact_path.relative_to(ROOT)),
            "threshold": float(threshold),
            "mean_abs_shap_csv": str((REPORT_DIR / f"{model_name}_validation_mean_abs_shap.csv").relative_to(ROOT)),
            "beeswarm_plot": str(beeswarm_plot.relative_to(ROOT)),
            "mean_abs_shap_plot": str(mean_plot.relative_to(ROOT)),
            "top_features": importance.head(10).to_dict(orient="records"),
            "local_examples": local,
        }

    report_path = REPORT_DIR / f"creditcard_treeshap_{args.feature_set.lower()}.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path.relative_to(ROOT)), "models_processed": sum(item.get("status") == "complete" for item in summary["models"].values())}, indent=2))


if __name__ == "__main__":
    main()
