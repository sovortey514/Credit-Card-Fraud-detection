"""Compare cost-sensitive weighting with SMOTE on chronological card-fraud splits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import tracemalloc

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from imblearn.over_sampling import BorderlineSMOTE, SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.fraud_detection.preprocessing_pipeline import F0_FEATURES, F1_FEATURES


DATA_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports" / "models"
MODEL_DIR = ROOT / "models" / "creditcard"
SEED = 42
TARGET = "Class"
INTERACTION_FEATURES = [
    "V14_x_V17", "V14_x_V12", "V14_x_V10",
    "V17_x_V12", "V17_x_V10", "V12_x_V10",
]
F1_ALL_FEATURES = [*F0_FEATURES, *F1_FEATURES, *INTERACTION_FEATURES]


def make_model(name: str, strategy: str, positive_weight: float):
    """Create the same model family with either weighting or SMOTE handling."""
    weighted = strategy == "class_weight"
    if name == "logistic_regression":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                class_weight="balanced" if weighted else None,
                max_iter=1_000,
                random_state=SEED,
            )),
        ])
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            class_weight="balanced" if weighted else None,
            n_jobs=-1,
            random_state=SEED,
        )
    if name == "xgboost":
        return XGBClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=positive_weight if weighted else 1.0,
            random_state=SEED,
            eval_metric="logloss",
            n_jobs=-1,
        )
    raise ValueError(f"Unknown model: {name}")


def make_sampler(strategy: str):
    """Create a sampler that is fitted only on the current training data."""
    if strategy == "smote":
        return SMOTE(sampling_strategy=0.1, random_state=SEED)
    if strategy == "borderline_smote":
        return BorderlineSMOTE(sampling_strategy=0.1, random_state=SEED)
    if strategy == "class_weight":
        return None
    raise ValueError(f"Unknown imbalance strategy: {strategy}")


def evaluate(model, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
    probabilities = model.predict_proba(X)[:, 1]
    predictions = probabilities >= 0.5
    true_negative, false_positive, _, _ = confusion_matrix(
        y, predictions, labels=[0, 1]
    ).ravel()
    return {
        "average_precision": float(average_precision_score(y, probabilities)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "precision_at_0_5": float(precision_score(y, predictions, zero_division=0)),
        "recall_at_0_5": float(recall_score(y, predictions, zero_division=0)),
        "f1_at_0_5": float(f1_score(y, predictions, zero_division=0)),
        "false_positive_rate_at_0_5": float(
            false_positive / (false_positive + true_negative)
        ),
    }


def run(feature_set: str, model_names: list[str]) -> dict[str, object]:
    train = pd.read_parquet(DATA_DIR / "creditcard_train_features.parquet")
    validation = pd.read_parquet(DATA_DIR / "creditcard_validation_features.parquet")
    test = pd.read_parquet(DATA_DIR / "creditcard_test_features.parquet")
    features = F0_FEATURES if feature_set == "F0" else F1_ALL_FEATURES

    X_train, y_train = train[features], train[TARGET].astype(int)
    X_validation, y_validation = validation[features], validation[TARGET].astype(int)
    X_test, y_test = test[features], test[TARGET].astype(int)
    negative = int((y_train == 0).sum())
    positive = int((y_train == 1).sum())
    positive_weight = negative / positive

    results: dict[str, object] = {
        "dataset": "Kaggle ULB Credit Card Fraud Detection",
        "feature_set": feature_set,
        "features": features,
        "seed": SEED,
        "train_rows": len(train),
        "validation_rows": len(validation),
        "test_rows": len(test),
        "training_fraud_count": positive,
        "training_legitimate_count": negative,
        "xgboost_scale_pos_weight": positive_weight,
        "synthetic_sampling_strategy": 0.1,
        "validation_and_test_sampling": "none",
        "validation_and_test_resampled": False,
        "models": {},
    }

    for strategy in ("class_weight", "smote", "borderline_smote"):
        sampler = make_sampler(strategy)
        fit_start = time.perf_counter()
        if sampler is not None:
            resample_start = time.perf_counter()
            X_fit_array, y_fit_array = sampler.fit_resample(X_train, y_train)
            resample_seconds = time.perf_counter() - resample_start
            X_fit = pd.DataFrame(X_fit_array, columns=features)
            y_fit = pd.Series(y_fit_array, name=TARGET)
        else:
            X_fit, y_fit = X_train, y_train
            resample_seconds = 0.0

        for model_name in model_names:
            model = make_model(model_name, strategy, positive_weight)
            model_start = time.perf_counter()
            tracemalloc.start()
            model.fit(X_fit, y_fit)
            model_fit_seconds = time.perf_counter() - model_start
            _, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            key = f"{model_name}_{strategy}"
            results["models"][key] = {
                "model": model_name,
                "strategy": strategy,
                "fit_rows": len(X_fit),
                "fit_fraud_count": int(y_fit.sum()),
                "fit_legitimate_count": int((y_fit == 0).sum()),
                "resampling_seconds": float(resample_seconds),
                "model_fit_seconds": float(model_fit_seconds),
                "total_training_seconds": float(time.perf_counter() - fit_start),
                "peak_traced_memory_mb": float(peak_memory / (1024 * 1024)),
                "validation": evaluate(model, X_validation, y_validation),
                "test": evaluate(model, X_test, y_test),
            }
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            import joblib
            joblib.dump(
                {"model": model, "features": features, "strategy": strategy},
                MODEL_DIR / f"{model_name}_{strategy}_{feature_set.lower()}.joblib",
            )

    return results


def save_report(results: dict[str, object], feature_set: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"creditcard_imbalance_{feature_set.lower()}.json"
    report_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    rows = []
    for key, metrics in results["models"].items():
        rows.append({
            "model_strategy": key,
            "validation_average_precision": metrics["validation"]["average_precision"],
            "validation_roc_auc": metrics["validation"]["roc_auc"],
            "validation_false_positive_rate": metrics["validation"]["false_positive_rate_at_0_5"],
            "test_average_precision": metrics["test"]["average_precision"],
            "test_roc_auc": metrics["test"]["roc_auc"],
            "test_false_positive_rate": metrics["test"]["false_positive_rate_at_0_5"],
            "total_training_seconds": metrics["total_training_seconds"],
            "peak_traced_memory_mb": metrics["peak_traced_memory_mb"],
        })
    table = pd.DataFrame(rows)
    table.to_csv(REPORT_DIR / f"creditcard_imbalance_{feature_set.lower()}.csv", index=False)

    figure, axes = plt.subplots(1, 3, figsize=(19, 5))
    table.plot.bar(x="model_strategy", y="validation_average_precision", ax=axes[0], legend=False)
    axes[0].set_title("Validation Average Precision")
    axes[0].set_ylabel("Average precision")
    axes[0].tick_params(axis="x", rotation=35)
    table.plot.bar(x="model_strategy", y="test_average_precision", ax=axes[1], legend=False)
    axes[1].set_title("Held-out Test Average Precision")
    axes[1].set_ylabel("Average precision")
    axes[1].tick_params(axis="x", rotation=35)
    table.plot.bar(x="model_strategy", y="validation_false_positive_rate", ax=axes[2], legend=False)
    axes[2].set_title("Validation False Positive Rate")
    axes[2].set_ylabel("FPR at threshold 0.5")
    axes[2].tick_params(axis="x", rotation=35)
    figure.tight_layout()
    figure.savefig(REPORT_DIR / f"creditcard_imbalance_{feature_set.lower()}.png", dpi=160)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-set", choices=("F0", "F1"), default="F1")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=("logistic_regression", "random_forest", "xgboost"),
        default=["logistic_regression", "random_forest", "xgboost"],
    )
    args = parser.parse_args()
    results = run(args.feature_set, args.models)
    save_report(results, args.feature_set)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
