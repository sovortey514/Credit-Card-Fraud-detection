"""Calibrate fraud-decision thresholds on validation data.

Threshold selection uses validation probabilities only. The held-out test set is
used afterward for an unbiased comparison of the selected threshold with 0.50.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "models" / "creditcard"
REPORT_DIR = ROOT / "reports" / "models"
TARGET = "Class"
SEED = 42
MIN_RECALL = 0.85
THRESHOLDS = np.round(np.linspace(0.01, 0.99, 99), 2)


def metrics_at_threshold(y_true: pd.Series, probabilities: np.ndarray, threshold: float) -> dict[str, float]:
    predictions = probabilities >= threshold
    true_negative, false_positive, false_negative, true_positive = confusion_matrix(
        y_true, predictions, labels=[0, 1]
    ).ravel()
    negatives = true_negative + false_positive
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "false_positive_rate": float(false_positive / negatives) if negatives else 0.0,
        "false_alarms_per_1000": float(false_positive / negatives * 1000) if negatives else 0.0,
        "true_positive": int(true_positive),
        "false_positive": int(false_positive),
        "true_negative": int(true_negative),
        "false_negative": int(false_negative),
    }


def calibrate(
    y_validation: pd.Series,
    probabilities: np.ndarray,
    min_recall: float,
) -> tuple[dict[str, float], list[dict[str, float]]]:
    sweep = [metrics_at_threshold(y_validation, probabilities, threshold) for threshold in THRESHOLDS]
    eligible = [row for row in sweep if row["recall"] >= min_recall]
    if not eligible:
        raise RuntimeError(f"No threshold from {THRESHOLDS[0]} to {THRESHOLDS[-1]} reaches recall >= {min_recall}.")
    selected = min(eligible, key=lambda row: (row["false_positive_rate"], -row["threshold"]))
    return selected, sweep


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-set", choices=("F0", "F1"), default="F1")
    parser.add_argument("--min-recall", type=float, default=MIN_RECALL)
    args = parser.parse_args()

    validation = pd.read_parquet(DATA_DIR / "creditcard_validation_features.parquet")
    test = pd.read_parquet(DATA_DIR / "creditcard_test_features.parquet")
    y_validation = validation[TARGET].astype(int)
    y_test = test[TARGET].astype(int)

    suffix = f"_{args.feature_set.lower()}"
    artifacts = sorted(MODEL_DIR.glob(f"*_*{suffix}.joblib"))
    if not artifacts:
        raise FileNotFoundError(f"No model artifacts found matching *_*{suffix}.joblib in {MODEL_DIR}")

    report: dict[str, object] = {
        "dataset": "Kaggle ULB Credit Card Fraud Detection",
        "feature_set": args.feature_set,
        "seed": SEED,
        "threshold_grid": [float(value) for value in THRESHOLDS],
        "calibration_split": "validation_only",
        "test_split_used_for_threshold_selection": False,
        "target_recall": args.min_recall,
        "models": {},
        "missing_expected_artifacts": [],
    }

    plot_rows: list[dict[str, object]] = []
    for artifact_path in artifacts:
        bundle = joblib.load(artifact_path)
        model = bundle["model"]
        features = bundle["features"]
        model_name = artifact_path.stem
        validation_probabilities = model.predict_proba(validation[features])[:, 1]
        test_probabilities = model.predict_proba(test[features])[:, 1]
        selected, sweep = calibrate(y_validation, validation_probabilities, args.min_recall)
        default_validation = metrics_at_threshold(y_validation, validation_probabilities, 0.50)
        default_test = metrics_at_threshold(y_test, test_probabilities, 0.50)
        calibrated_test = metrics_at_threshold(y_test, test_probabilities, selected["threshold"])

        report["models"][model_name] = {
            "artifact": str(artifact_path.relative_to(ROOT)),
            "model": bundle.get("model_name", model_name),
            "strategy": bundle.get("strategy", "unknown"),
            "selected_threshold": selected["threshold"],
            "validation_default_threshold_0_50": default_validation,
            "validation_calibrated_threshold": selected,
            "test_default_threshold_0_50": default_test,
            "test_calibrated_threshold": calibrated_test,
            "validation_sweep": sweep,
        }
        plot_rows.append({"model": model_name, "sweep": sweep})

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"creditcard_threshold_calibration_{args.feature_set.lower()}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    rows = []
    for model_name, metrics in report["models"].items():
        for split_name, default_values, calibrated_values in (
            (
                "validation",
                metrics["validation_default_threshold_0_50"],
                metrics["validation_calibrated_threshold"],
            ),
            (
                "test",
                metrics["test_default_threshold_0_50"],
                metrics["test_calibrated_threshold"],
            ),
        ):
            for mode, values in (("default_0_50", default_values), ("calibrated", calibrated_values)):
                rows.append({
                    "model": model_name,
                    "split": split_name,
                    "threshold_mode": mode,
                    "threshold": values["threshold"],
                    "precision": values["precision"],
                    "recall": values["recall"],
                    "f1": values["f1"],
                    "false_positive_rate": values["false_positive_rate"],
                    "false_alarms_per_1000": values["false_alarms_per_1000"],
                })
    pd.DataFrame(rows).to_csv(REPORT_DIR / f"creditcard_threshold_calibration_{args.feature_set.lower()}.csv", index=False)

    figure, axes = plt.subplots(1, 2, figsize=(16, 5))
    for item in plot_rows:
        sweep_table = pd.DataFrame(item["sweep"])
        axes[0].plot(sweep_table["threshold"], sweep_table["recall"], label=item["model"])
        axes[1].plot(sweep_table["threshold"], sweep_table["false_alarms_per_1000"], label=item["model"])
    axes[0].axhline(args.min_recall, color="black", linestyle="--", label=f"Recall target ({args.min_recall:.0%})")
    axes[0].set(title="Validation recall by threshold", xlabel="Decision threshold", ylabel="Recall")
    axes[1].set(title="Validation false alarms by threshold", xlabel="Decision threshold", ylabel="False alarms per 1,000")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(REPORT_DIR / f"creditcard_threshold_calibration_{args.feature_set.lower()}.png", dpi=160)
    plt.close(figure)

    print(json.dumps({
        "report": str(report_path.relative_to(ROOT)),
        "csv": str((REPORT_DIR / f"creditcard_threshold_calibration_{args.feature_set.lower()}.csv").relative_to(ROOT)),
        "models_processed": len(report["models"]),
    }, indent=2))


if __name__ == "__main__":
    main()
