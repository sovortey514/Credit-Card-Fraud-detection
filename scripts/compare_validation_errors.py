"""Compare F1 classifiers on chronological validation at a fixed threshold."""
import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import average_precision_score, confusion_matrix, precision_score, recall_score

from scripts.compare_feature_baselines import prepare

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/validation_errors"
MODELS = ROOT / "models/feature_baselines"


def measures(y, scores, threshold):
    y, scores = np.asarray(y), np.asarray(scores)
    tn, fp, fn, tp = confusion_matrix(y, scores >= threshold, labels=[0, 1]).ravel()
    return {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            "precision": float(precision_score(y, scores >= threshold, zero_division=0)),
            "recall": float(recall_score(y, scores >= threshold, zero_division=0)),
            "false_alarms_per_1000_legitimate": float(fp / (fp + tn) * 1000),
            "alerts": int(fp + tp)}


def main():
    train = pd.read_parquet(ROOT / "data/processed/creditcard_train.parquet").reset_index(drop=True)
    validation = pd.read_parquet(ROOT / "data/processed/creditcard_validation.parquet").reset_index(drop=True)
    preprocessor, x_train, x_val = prepare(train, validation, "F1")
    lgbm = LGBMClassifier(n_estimators=200, max_depth=12, class_weight="balanced", random_state=42, n_jobs=4, verbosity=-1).fit(x_train, train["Class"])
    joblib.dump({"model": lgbm, "preprocessor": preprocessor, "feature_set": "F1"}, MODELS / "lightgbm_f1.joblib")
    paths = {"Logistic Regression": MODELS / "logistic_regression_f1.joblib", "Random Forest": MODELS / "random_forest_f1.joblib", "LightGBM": MODELS / "lightgbm_f1.joblib", "XGBoost + GA": ROOT / "models/xgboost_genetic/genetic.joblib"}
    y = validation["Class"].to_numpy()
    results = {"partition": "chronological validation", "rows": len(y), "fraud": int(y.sum()), "threshold": 0.5, "positive_rule": "score >= threshold", "models": {}}
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    for ax, (name, path) in zip(axes, paths.items()):
        bundle = joblib.load(path)
        transformer = bundle["preprocessor"].named_steps["features"]
        _, history, last_time = transformer.transform_with_history(train)
        features, _, _ = transformer.transform_with_history(validation, history, last_time)
        scores = bundle["model"].predict_proba(features)[:, 1]
        summary = measures(y, scores, 0.5)
        summary["average_precision"] = float(average_precision_score(y, scores))
        summary["thresholds"] = {str(t): measures(y, scores, t) for t in (0.1, 0.25, 0.5, 0.75, 0.9)}
        summary["false_positive_amount_median"] = float(validation.loc[(y == 0) & (scores >= 0.5), "Amount"].median()) if summary["fp"] else None
        summary["false_negative_amount_median"] = float(validation.loc[(y == 1) & (scores < 0.5), "Amount"].median()) if summary["fn"] else None
        results["models"][name] = summary
        matrix = np.array([[summary["tn"], summary["fp"]], [summary["fn"], summary["tp"]]])
        ax.imshow(matrix, cmap="Blues")
        for row in range(2):
            for col in range(2):
                ax.text(col, row, f"{matrix[row, col]:,}", ha="center", va="center", color="white" if matrix[row, col] > matrix.max() / 2 else "black")
        ax.set(title=name, xticks=[0, 1], yticks=[0, 1], xticklabels=["legitimate", "fraud"], yticklabels=["legitimate", "fraud"], xlabel="Predicted", ylabel="Actual")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT / "confusion_matrices.png", dpi=160)
    plt.close(fig)
    (OUTPUT / "comparison.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
