"""Compare the 30/37-feature contracts using chronological folds."""
import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.fraud_detection.feature_contract import build_feature_pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUTPUT = ROOT / "reports/feature_baselines"
MODELS = ROOT / "models/feature_baselines"


def make_model(name):
    if name == "logistic_regression":
        return make_pipeline(StandardScaler(), LogisticRegression(penalty="l2", class_weight="balanced", max_iter=1000, random_state=42))
    return RandomForestClassifier(n_estimators=200, max_depth=12, class_weight="balanced", random_state=42, n_jobs=-1)


def prepare(train, later, feature_set):
    pipeline = build_feature_pipeline(feature_set).fit(train)
    transformer = pipeline.named_steps["features"]
    x_train, history, last_time = transformer.transform_with_history(train)
    x_later, _, _ = transformer.transform_with_history(later, history, last_time)
    return pipeline, x_train, x_later


def main():
    train = pd.read_parquet(DATA / "creditcard_train.parquet").reset_index(drop=True)
    validation = pd.read_parquet(DATA / "creditcard_validation.parquet").reset_index(drop=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    results = {"seed": 42, "folds": 5, "validation_rows": len(validation), "test_used": False, "models": {}}
    predictions = {}
    for feature_set in ("F0", "F1"):
        for name in ("logistic_regression", "random_forest"):
            key = f"{name}_{feature_set}"
            folds = []
            for number, (ti, vi) in enumerate(TimeSeriesSplit(n_splits=5).split(train), 1):
                earlier, later = train.iloc[ti], train.iloc[vi]
                _, x_train, x_valid = prepare(earlier, later, feature_set)
                model = make_model(name).fit(x_train, earlier["Class"])
                score = model.predict_proba(x_valid)[:, 1]
                folds.append({"fold": number, "train_rows": len(ti), "validation_rows": len(vi), "average_precision": float(average_precision_score(later["Class"], score)), "roc_auc": float(roc_auc_score(later["Class"], score))})
                print(f"{key} fold {number} complete", flush=True)
            transformer, x_train, x_valid = prepare(train, validation, feature_set)
            model = make_model(name).fit(x_train, train["Class"])
            score = model.predict_proba(x_valid)[:, 1]
            predictions[key] = score
            results["models"][key] = {"folds": folds, "mean_average_precision": float(np.mean([f["average_precision"] for f in folds])), "mean_roc_auc": float(np.mean([f["roc_auc"] for f in folds])), "validation_average_precision": float(average_precision_score(validation["Class"], score)), "validation_roc_auc": float(roc_auc_score(validation["Class"], score))}
            joblib.dump({"model": model, "preprocessor": transformer, "feature_set": feature_set}, MODELS / f"{key.lower()}.joblib")
            (OUTPUT / "comparison.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    for kind in ("pr", "roc"):
        plt.figure(figsize=(8, 6))
        for name, score in predictions.items():
            if kind == "pr":
                precision, recall, _ = precision_recall_curve(validation["Class"], score)
                plt.plot(recall, precision, label=f"{name} AP={results['models'][name]['validation_average_precision']:.3f}")
            else:
                fpr, tpr, _ = roc_curve(validation["Class"], score)
                plt.plot(fpr, tpr, label=f"{name} AUC={results['models'][name]['validation_roc_auc']:.3f}")
        plt.xlabel("Recall" if kind == "pr" else "False positive rate")
        plt.ylabel("Precision" if kind == "pr" else "True positive rate")
        plt.title(f"Chronological validation {kind.upper()} curves")
        plt.legend()
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(OUTPUT / f"validation_{kind}.png", dpi=160)
        plt.close()
    print(json.dumps(results, indent=2), flush=True)


if __name__ == "__main__":
    main()
