"""Benchmark raw versus k=50-medoid TreeSHAP for final tree models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.cluster import KMeans

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "models" / "creditcard"
REPORT_DIR = ROOT / "reports" / "explainability"
SEED = 42
MEDOID_COUNT = 50
MODEL_ARTIFACTS = {
    "random_forest": "random_forest_class_weight_f1.joblib",
    "xgboost": "xgboost_class_weight_f1.joblib",
}


def shap_values_for_class_one(explainer: shap.TreeExplainer, X: pd.DataFrame) -> np.ndarray:
    result = explainer.shap_values(X, check_additivity=False)
    if isinstance(result, list):
        return np.asarray(result[1] if len(result) > 1 else result[0])
    values = result.values if hasattr(result, "values") else np.asarray(result)
    return values[:, :, 1] if values.ndim == 3 else values


def make_medoids(X_train: pd.DataFrame, k: int) -> tuple[pd.DataFrame, dict[str, object]]:
    """Fit K-Means and return actual training rows nearest to its centroids."""
    kmeans = KMeans(n_clusters=k, random_state=SEED, n_init=3, max_iter=100)
    start = time.perf_counter()
    kmeans.fit(X_train)
    fit_seconds = time.perf_counter() - start
    distances = ((X_train.to_numpy()[:, None, :] - kmeans.cluster_centers_[None, :, :]) ** 2).sum(axis=2)
    nearest_positions = np.argmin(distances, axis=0)
    # Protect against duplicate rows being selected for multiple centroids.
    selected_positions = []
    used = set()
    for cluster_index, position in enumerate(nearest_positions):
        candidates = np.argsort(distances[:, cluster_index])
        selected = next((int(candidate) for candidate in candidates if int(candidate) not in used), int(position))
        used.add(selected)
        selected_positions.append(selected)
    medoids = X_train.iloc[selected_positions].reset_index(drop=True)
    return medoids, {"k": k, "fit_rows": len(X_train), "fit_seconds": fit_seconds}


def benchmark(explainer: shap.TreeExplainer, X: pd.DataFrame) -> dict[str, float]:
    timings = []
    for index in range(len(X)):
        row = X.iloc[[index]]
        start = time.perf_counter()
        shap_values_for_class_one(explainer, row)
        timings.append((time.perf_counter() - start) * 1000)
    return {
        "transactions": len(timings),
        "mean_ms_per_transaction": float(np.mean(timings)),
        "median_ms_per_transaction": float(np.median(timings)),
        "p95_ms_per_transaction": float(np.percentile(timings, 95)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-set", choices=("F0", "F1"), default="F1")
    parser.add_argument("--analysis-rows", type=int, default=1000, help="Validation rows used for ranking fidelity.")
    parser.add_argument("--benchmark-rows", type=int, default=100, help="Validation rows used for latency timing.")
    args = parser.parse_args()

    train = pd.read_parquet(DATA_DIR / "creditcard_train_features.parquet")
    validation = pd.read_parquet(DATA_DIR / "creditcard_validation_features.parquet")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    medoid_report: dict[str, object] = {}
    results: dict[str, object] = {
        "dataset": "Kaggle ULB Credit Card Fraud Detection",
        "feature_set": args.feature_set,
        "seed": SEED,
        "medoid_method": "KMeans centroids with nearest actual training row selected as medoid",
        "medoid_count": MEDOID_COUNT,
        "analysis_rows": min(args.analysis_rows, len(validation)),
        "benchmark_rows": min(args.benchmark_rows, len(validation)),
        "models": {},
    }

    for model_name, artifact_name in MODEL_ARTIFACTS.items():
        artifact_path = MODEL_DIR / artifact_name
        if not artifact_path.exists():
            results["models"][model_name] = {"status": "missing", "artifact": str(artifact_path.relative_to(ROOT))}
            continue
        bundle = joblib.load(artifact_path)
        model = bundle["model"]
        features = bundle["features"]
        X_train = train[features]
        X_analysis = validation[features].iloc[: args.analysis_rows]
        X_benchmark = validation[features].iloc[: args.benchmark_rows]

        medoids, medoid_metadata = make_medoids(X_train, MEDOID_COUNT)
        medoid_path = REPORT_DIR / f"{model_name}_background_medoids_k50.joblib"
        joblib.dump({"medoids": medoids, "features": features, "metadata": medoid_metadata}, medoid_path)

        raw_explainer = shap.TreeExplainer(model)
        medoid_explainer = shap.TreeExplainer(
            model,
            data=medoids,
            feature_perturbation="interventional",
        )
        exact_values = shap_values_for_class_one(raw_explainer, X_analysis)
        medoid_values = shap_values_for_class_one(medoid_explainer, X_analysis)
        exact_importance = pd.Series(np.abs(exact_values).mean(axis=0), index=features).sort_values(ascending=False)
        medoid_importance = pd.Series(np.abs(medoid_values).mean(axis=0), index=features).sort_values(ascending=False)
        exact_top3 = list(exact_importance.head(3).index)
        medoid_top3 = list(medoid_importance.head(3).index)
        overlap = len(set(exact_top3) & set(medoid_top3))

        raw_bundle_path = MODEL_DIR / f"{model_name}_treeshap_raw_f1.joblib"
        medoid_bundle_path = MODEL_DIR / f"{model_name}_treeshap_medoids50_f1.joblib"
        joblib.dump({"model": model, "explainer": raw_explainer, "features": features, "mode": "raw"}, raw_bundle_path)
        joblib.dump({"model": model, "explainer": medoid_explainer, "features": features, "mode": "k50_medoids", "background": medoids}, medoid_bundle_path)

        results["models"][model_name] = {
            "status": "complete",
            "source_artifact": str(artifact_path.relative_to(ROOT)),
            "medoid_background": str(medoid_path.relative_to(ROOT)),
            "raw_bundle": str(raw_bundle_path.relative_to(ROOT)),
            "medoid_bundle": str(medoid_bundle_path.relative_to(ROOT)),
            "medoid_metadata": medoid_metadata,
            "latency_raw": benchmark(raw_explainer, X_benchmark),
            "latency_k50_medoids": benchmark(medoid_explainer, X_benchmark),
            "top3_exact_raw": exact_top3,
            "top3_k50_medoids": medoid_top3,
            "top3_overlap_count": overlap,
            "top3_overlap_ratio": overlap / 3,
            "exact_mean_abs_shap": {feature: float(exact_importance[feature]) for feature in exact_top3},
            "medoid_mean_abs_shap": {feature: float(medoid_importance[feature]) for feature in medoid_top3},
        }

    report_path = REPORT_DIR / f"creditcard_treeshap_latency_{args.feature_set.lower()}.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    rows = []
    for model_name, item in results["models"].items():
        if item.get("status") != "complete":
            continue
        for mode, metrics in (("raw", item["latency_raw"]), ("k50_medoids", item["latency_k50_medoids"])):
            rows.append({"model": model_name, "background": mode, **metrics})
    pd.DataFrame(rows).to_csv(REPORT_DIR / f"creditcard_treeshap_latency_{args.feature_set.lower()}.csv", index=False)
    print(json.dumps({"report": str(report_path.relative_to(ROOT)), "models_processed": len(rows) // 2}, indent=2))


if __name__ == "__main__":
    main()
