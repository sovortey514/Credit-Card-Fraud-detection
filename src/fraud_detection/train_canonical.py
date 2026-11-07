"""Train the baseline models on the canonical Week 4 Parquet partitions."""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import PROCESSED_DIR, SEED
from .features import FEATURES, make_features


def main():
    parts = {name: pd.read_parquet(PROCESSED_DIR / f"{name}.parquet")
             for name in ("train", "validation", "test")}
    x_train, x_val = make_features(parts["train"]), make_features(parts["validation"])
    y_train, y_val = parts["train"].isFraud.astype(int), parts["validation"].isFraud.astype(int)
    models = {
        "logistic_regression": Pipeline([
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=500, class_weight="balanced", random_state=SEED)),
        ]),
        "random_forest": RandomForestClassifier(
            n_estimators=100, max_depth=12, class_weight="balanced", random_state=SEED, n_jobs=-1
        ),
    }
    results = {}
    best_name, best_score, best_model = None, -1.0, None
    for name, model in models.items():
        model.fit(x_train, y_train)
        score = float(average_precision_score(y_val, model.predict_proba(x_val)[:, 1]))
        results[name] = {"validation_average_precision": score}
        if score > best_score:
            best_name, best_score, best_model = name, score, model
    Path("models").mkdir(exist_ok=True)
    joblib.dump({"model": best_model, "model_name": best_name, "features": FEATURES},
                "models/fraud_model_canonical.joblib")
    Path("reports").mkdir(exist_ok=True)
    Path("reports/canonical_model_results.json").write_text(
        json.dumps({"selected_model": best_name, "results": results}, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
