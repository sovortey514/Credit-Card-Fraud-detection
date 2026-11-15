"""Compare credit-card baseline models on F0 and F1 feature sets."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.fraud_detection.preprocessing_pipeline import F0_FEATURES, F1_FEATURES


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports" / "models"
MODEL_DIR = ROOT / "models" / "creditcard"
TARGET = "Class"
SEED = 42

# F1 is the enhanced feature set: F0 plus engineered temporal, amount, and
# PCA-interaction features.
INTERACTION_FEATURES = [
    "V14_x_V17",
    "V14_x_V12",
    "V14_x_V10",
    "V17_x_V12",
    "V17_x_V10",
    "V12_x_V10",
]
F1_ALL_FEATURES = [*F0_FEATURES, *F1_FEATURES, *INTERACTION_FEATURES]


def make_models() -> dict[str, object]:
    return {
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        penalty="l2",
                        class_weight="balanced",
                        max_iter=1_000,
                        random_state=SEED,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            class_weight="balanced",
            n_jobs=-1,
            random_state=SEED,
        ),
    }


def cross_validate_model(model, X: pd.DataFrame, y: pd.Series) -> dict[str, object]:
    splitter = TimeSeriesSplit(n_splits=5)
    fold_results: list[dict[str, float | int]] = []
    for fold, (train_index, validation_index) in enumerate(splitter.split(X), start=1):
        fold_model = make_models()["logistic_regression"] if isinstance(model, Pipeline) else make_models()["random_forest"]
        fold_model.fit(X.iloc[train_index], y.iloc[train_index])
        probabilities = fold_model.predict_proba(X.iloc[validation_index])[:, 1]
        fold_results.append(
            {
                "fold": fold,
                "average_precision": float(
                    average_precision_score(y.iloc[validation_index], probabilities)
                ),
                "roc_auc": float(roc_auc_score(y.iloc[validation_index], probabilities)),
            }
        )
    return {
        "folds": fold_results,
        "mean_average_precision": float(np.mean([item["average_precision"] for item in fold_results])),
        "mean_roc_auc": float(np.mean([item["roc_auc"] for item in fold_results])),
    }


def main() -> None:
    train = pd.read_parquet(DATA_DIR / "creditcard_train_features.parquet")
    validation = pd.read_parquet(DATA_DIR / "creditcard_validation_features.parquet")
    y_train = train[TARGET].astype(int)
    y_validation = validation[TARGET].astype(int)

    feature_sets = {"F0": F0_FEATURES, "F1": F1_ALL_FEATURES}
    results: dict[str, object] = {
        "dataset": "Kaggle ULB Credit Card Fraud Detection",
        "cv": "5-fold TimeSeriesSplit on chronological training partition",
        "validation_partition": "15% chronological validation split",
        "models": {},
    }
    validation_predictions: dict[str, np.ndarray] = {}

    for feature_set_name, features in feature_sets.items():
        X_train = train[features]
        X_validation = validation[features]
        for model_name, model in make_models().items():
            key = f"{model_name}_{feature_set_name}"
            cv_results = cross_validate_model(model, X_train, y_train)
            model.fit(X_train, y_train)
            probabilities = model.predict_proba(X_validation)[:, 1]
            validation_predictions[key] = probabilities
            results["models"][key] = {
                "model": model_name,
                "feature_set": feature_set_name,
                "features": features,
                "parameters": model.get_params(),
                "cv": cv_results,
                "validation_average_precision": float(
                    average_precision_score(y_validation, probabilities)
                ),
                "validation_roc_auc": float(roc_auc_score(y_validation, probabilities)),
            }
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            joblib.dump(
                {"model": model, "features": features, "feature_set": feature_set_name},
                MODEL_DIR / f"{model_name}_{feature_set_name.lower()}.joblib",
            )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "creditcard_f0_f1_comparison.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )

    plt.figure(figsize=(8, 6))
    for key, probabilities in validation_predictions.items():
        precision, recall, _ = precision_recall_curve(y_validation, probabilities)
        score = results["models"][key]["validation_average_precision"]
        plt.plot(recall, precision, label=f"{key} AP={score:.4f}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Credit-card fraud validation Precision-Recall curves")
    plt.legend(loc="best")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(REPORT_DIR / "creditcard_validation_precision_recall.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 6))
    for key, probabilities in validation_predictions.items():
        false_positive_rate, true_positive_rate, _ = roc_curve(y_validation, probabilities)
        score = results["models"][key]["validation_roc_auc"]
        plt.plot(false_positive_rate, true_positive_rate, label=f"{key} ROC-AUC={score:.4f}")
    plt.plot([0, 1], [0, 1], "k--", alpha=0.5)
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("Credit-card fraud validation ROC curves")
    plt.legend(loc="best")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(REPORT_DIR / "creditcard_validation_roc.png", dpi=160)
    plt.close()

    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
