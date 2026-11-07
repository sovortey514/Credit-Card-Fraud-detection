"""Train and evaluate CatBoost and XGBoost fraud classifiers."""

from __future__ import annotations

import os

import joblib
from catboost import CatBoostClassifier
from sklearn.metrics import (
    auc,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
)
from xgboost import XGBClassifier


def _print_results(name, y_test, predictions, probabilities):
    precision, recall, _ = precision_recall_curve(y_test, probabilities)
    # sklearn returns recall in descending order; sort before trapezoidal AUC.
    order = recall.argsort()
    pr_auc = auc(recall[order], precision[order])
    print(f"\n--- {name} Results ---")
    print(classification_report(y_test, predictions, digits=4))
    print(f"PR-AUC Score: {pr_auc:.4f}")
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, predictions))
    return pr_auc


def train_and_evaluate_models(
    X_train_res,
    X_test,
    y_train_res,
    y_test,
    model_dir="models",
):
    """Train models on resampled training data and evaluate untouched test data."""
    os.makedirs(model_dir, exist_ok=True)

    print("\n================ Training CatBoost ================")
    cat_model = CatBoostClassifier(
        iterations=500,
        learning_rate=0.05,
        depth=6,
        verbose=100,
        random_seed=42,
        loss_function="Logloss",
    )
    cat_model.fit(X_train_res, y_train_res)
    cat_predictions = cat_model.predict(X_test).ravel()
    cat_probabilities = cat_model.predict_proba(X_test)[:, 1]
    _print_results("CatBoost", y_test, cat_predictions, cat_probabilities)
    joblib.dump(
        cat_model,
        os.path.join(model_dir, "catboost_fraud_model.joblib"),
    )

    print("\n================ Training XGBoost ================")
    xgb_model = XGBClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        random_state=42,
        eval_metric="logloss",
    )
    xgb_model.fit(X_train_res, y_train_res)
    xgb_predictions = xgb_model.predict(X_test)
    xgb_probabilities = xgb_model.predict_proba(X_test)[:, 1]
    _print_results("XGBoost", y_test, xgb_predictions, xgb_probabilities)
    joblib.dump(
        xgb_model,
        os.path.join(model_dir, "xgb_fraud_model.joblib"),
    )

    print(f"\nModels successfully saved to the '{model_dir}/' folder!")
    return cat_model, xgb_model
