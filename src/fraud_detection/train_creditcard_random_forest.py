from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_score, recall_score, f1_score, roc_auc_score


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed_creditcard"
MODEL_DIR = ROOT / "models" / "creditcard"
REPORT_DIR = ROOT / "reports" / "models"
FEATURES = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
TARGET = "Class"


def main():
    train = pd.read_csv(DATA_DIR / "train.csv")
    validation = pd.read_csv(DATA_DIR / "validation.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(train[FEATURES], train[TARGET])
    validation_probs = model.predict_proba(validation[FEATURES])[:, 1]
    thresholds = [i / 100 for i in range(1, 100)]
    threshold = max(thresholds, key=lambda t: f1_score(validation[TARGET], validation_probs >= t, zero_division=0))
    test_probs = model.predict_proba(test[FEATURES])[:, 1]
    predictions = test_probs >= threshold
    report = {
        "dataset": "Credit Card Fraud Detection",
        "features": FEATURES,
        "threshold": threshold,
        "validation_f1": f1_score(validation[TARGET], validation_probs >= threshold, zero_division=0),
        "test_average_precision": average_precision_score(test[TARGET], test_probs),
        "test_roc_auc": roc_auc_score(test[TARGET], test_probs),
        "test_precision": precision_score(test[TARGET], predictions, zero_division=0),
        "test_recall": recall_score(test[TARGET], predictions, zero_division=0),
        "test_f1": f1_score(test[TARGET], predictions, zero_division=0),
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "threshold": threshold}, MODEL_DIR / "random_forest.joblib")
    (REPORT_DIR / "creditcard_random_forest_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
