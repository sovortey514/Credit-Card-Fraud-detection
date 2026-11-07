import argparse
import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
)
from xgboost import XGBClassifier
from .features import make_features, FEATURES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/raw/paysim.csv")
    parser.add_argument("--model-dir", default="models")
    args = parser.parse_args()
    df = pd.read_csv(args.data)
    df = (
        df[df["type"].isin(["TRANSFER", "CASH_OUT"])]
        .sort_values("step", kind="stable")
        .reset_index(drop=True)
    )
    if len(df) < 50 or df["isFraud"].nunique() < 2:
        raise ValueError(
            "Need at least 50 transfer-related rows with both fraud classes"
        )
    # Chronological partitions: no random test-set shuffling.
    steps = sorted(df["step"].unique())
    if len(steps) < 5:
        raise ValueError("Need at least five distinct time steps")
    cut1, cut2 = steps[int(len(steps) * 0.6)], steps[int(len(steps) * 0.8)]
    train, val, test = (
        df[df.step < cut1],
        df[(df.step >= cut1) & (df.step < cut2)],
        df[df.step >= cut2],
    )
    if any(part.empty or part.isFraud.nunique() < 2 for part in (train, val, test)):
        raise ValueError(
            "Each chronological split must contain both classes. Use a larger representative dataset."
        )
    xtr, xv, xt = map(make_features, (train, val, test))
    ytr, yv, yt = (part.isFraud.astype(int) for part in (train, val, test))
    pos = int(ytr.sum())
    neg = len(ytr) - pos
    models = {
        "logistic_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=500, class_weight="balanced", random_state=42
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=12,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=42,
        ),
        "xgboost": XGBClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=neg / max(pos, 1),
            eval_metric="logloss",
            n_jobs=4,
            random_state=42,
        ),
    }
    results = []
    best = None
    for name, model in models.items():
        model.fit(xtr, ytr)
        scores = model.predict_proba(xv)[:, 1]
        ap = average_precision_score(yv, scores)
        # Tune threshold only on validation data; never on test data.
        thresholds = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        threshold = max(
            thresholds, key=lambda t: f1_score(yv, scores >= t, zero_division=0)
        )
        results.append(
            {
                "model": name,
                "validation_average_precision": float(ap),
                "validation_threshold": threshold,
            }
        )
        if best is None or ap > best[0]:
            best = (ap, name, model, threshold)
    _, name, model, threshold = best
    preds = model.predict_proba(xt)[:, 1]
    labels = preds >= threshold
    report = {
        "selected_model": name,
        "threshold": threshold,
        "features": FEATURES,
        "dataset_rows": len(df),
        "split_rows": {"train": len(train), "validation": len(val), "test": len(test)},
        "validation_comparison": results,
        "test_metrics": {
            "average_precision": float(average_precision_score(yt, preds)),
            "precision": float(precision_score(yt, labels, zero_division=0)),
            "recall": float(recall_score(yt, labels, zero_division=0)),
            "f1": float(f1_score(yt, labels, zero_division=0)),
        },
    }
    dest = Path(args.model_dir)
    dest.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "threshold": threshold,
            "model_name": name,
            "features": FEATURES,
        },
        dest / "fraud_model.joblib",
    )
    Path("reports").mkdir(exist_ok=True)
    (Path("reports") / "model_results.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
