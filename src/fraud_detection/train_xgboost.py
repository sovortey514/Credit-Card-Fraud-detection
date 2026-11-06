
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd

from xgboost import XGBClassifier
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports" / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "log_amount",
    "log_oldbalanceOrg",
    "step"
]

print("Loading prepared datasets...")

train = pd.read_csv(DATA_DIR / "train.csv")
validation = pd.read_csv(DATA_DIR / "validation.csv")
test = pd.read_csv(DATA_DIR / "test.csv")

assert train["step"].max() < validation["step"].min()
assert validation["step"].max() < test["step"].min()

X_train = train[FEATURES]
y_train = train["isFraud"]

X_val = validation[FEATURES]
y_val = validation["isFraud"]

X_test = test[FEATURES]
y_test = test["isFraud"]

# Account for imbalanced classes in training.
positive = int(y_train.sum())
negative = int(len(y_train) - positive)

scale_pos_weight = negative / positive

print(f"Scale positive weight: {scale_pos_weight:.2f}")
print("Training XGBoost...")

model = XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.9,
    objective="binary:logistic",
    eval_metric="aucpr",
    scale_pos_weight=scale_pos_weight,
    tree_method="hist",
    n_jobs=4,
    random_state=42
)

model.fit(X_train, y_train)

print("Evaluating validation data...")

val_probs = model.predict_proba(X_val)[:, 1]

thresholds = np.linspace(0.01, 0.99, 99)

best_threshold = 0.5
best_f1 = -1.0

for threshold in thresholds:
    predictions = (
        val_probs >= threshold
    ).astype(int)

    score = f1_score(
        y_val,
        predictions,
        zero_division=0
    )

    if score > best_f1:
        best_f1 = score
        best_threshold = float(threshold)

print(f"Selected threshold: {best_threshold:.2f}")
print(f"Validation F1: {best_f1:.4f}")

print("Evaluating test data...")

test_probs = model.predict_proba(X_test)[:, 1]

test_predictions = (
    test_probs >= best_threshold
).astype(int)

results = {
    "model": "XGBoost",
    "features": FEATURES,
    "threshold": best_threshold,
    "validation_f1": float(best_f1),
    "test_pr_auc": float(
        average_precision_score(y_test, test_probs)
    ),
    "test_roc_auc": float(
        roc_auc_score(y_test, test_probs)
    ),
    "test_precision": float(
        precision_score(
            y_test,
            test_predictions,
            zero_division=0
        )
    ),
    "test_recall": float(
        recall_score(
            y_test,
            test_predictions,
            zero_division=0
        )
    ),
    "test_f1": float(
        f1_score(
            y_test,
            test_predictions,
            zero_division=0
        )
    ),
    "confusion_matrix": confusion_matrix(
        y_test,
        test_predictions,
        labels=[0, 1]
    ).tolist()
}

print("\n===== XGBOOST RESULTS =====")

for key, value in results.items():
    print(f"{key}: {value}")

joblib.dump(
    {
        "model": model,
        "features": FEATURES,
        "threshold": best_threshold
    },
    MODEL_DIR / "xgboost.joblib"
)

with open(
    REPORT_DIR / "xgboost_results.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(results, f, indent=4)

print("\nXGBoost training completed!")
