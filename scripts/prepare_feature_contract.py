"""Fit and serialize F0/F1 pipelines and measure single-row transformation."""
import json
from pathlib import Path
from time import perf_counter
import joblib
import numpy as np
import pandas as pd

from src.fraud_detection.feature_contract import build_feature_pipeline

ROOT = Path(__file__).resolve().parents[1]
train = pd.read_parquet(ROOT / "data/processed/creditcard_train.parquet")
destination = ROOT / "models/feature_contract"
destination.mkdir(parents=True, exist_ok=True)
report = {}
for name in ("F0", "F1"):
    pipeline = build_feature_pipeline(name).fit(train)
    joblib.dump(pipeline, destination / f"{name.lower()}_preprocessing.joblib")
    transformer = pipeline.named_steps["features"]
    sample = train.iloc[:1200]
    history, last_time = [], None
    times = []
    for index, row in enumerate(sample.to_dict(orient="records")):
        started = perf_counter()
        _, history, last_time = transformer.transform_one(row, history, last_time)
        elapsed = (perf_counter() - started) * 1000
        if index >= 200:
            times.append(elapsed)
    report[name] = {"rows": len(times), "warmup_rows": 200, "method": "single validated mapping, explicit rolling history; excludes HTTP and schema validation", "mean_ms": float(np.mean(times)), "p95_ms": float(np.percentile(times, 95)), "target_mean_ms": 2.0}
    report[name]["mean_below_target"] = report[name]["mean_ms"] < 2.0
(destination / "latency.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
