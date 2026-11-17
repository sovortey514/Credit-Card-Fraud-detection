"""Score frozen artifacts once; retain predictions, provenance, and final tables.

The existing test partition has prior exposure. This run must not be described
as a first evaluation on an untouched test set. No fitting or tuning occurs here.
An exclusive receipt prevents a second run, including after an interrupted run.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate(y: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    y, scores = np.asarray(y), np.asarray(scores)
    if y.ndim != 1 or scores.shape != y.shape or set(np.unique(y)) != {0, 1}:
        raise ValueError("Aligned binary labels containing both classes are required")
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("Scores must be finite probabilities")
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Threshold must lie in [0, 1]")
    tn, fp, fn, tp = (int(x) for x in confusion_matrix(y, scores >= threshold, labels=[0, 1]).ravel())
    return {
        "threshold": float(threshold),
        "pr_auc_ap": float(average_precision_score(y, scores)),
        "roc_auc": float(roc_auc_score(y, scores)),
        "f1": 2 * tp / (2 * tp + fp + fn) if tp else 0.0,
        "recall": tp / (tp + fn),
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "false_alarms_per_1000_legitimate": 1000 * fp / (tn + fp),
        "false_alarms_per_1000_all": 1000 * fp / len(y),
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
    }


def frozen_spec(root: Path) -> tuple[list[dict], list[Path]]:
    calibration_path = root / "reports/models/creditcard_threshold_calibration_f1.json"
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    if calibration.get("calibration_split") != "validation_only" or calibration.get("test_split_used_for_threshold_selection") is not False:
        raise ValueError("Validation-only threshold provenance is required")
    if not calibration.get("models"):
        raise ValueError("No frozen calibrated models")
    specs = []
    for name, item in sorted(calibration["models"].items()):
        artifact = root / Path(item["artifact"].replace("\\", "/"))
        expected = root / "models/creditcard" / f"{name}.joblib"
        if artifact.resolve() != expected.resolve():
            raise ValueError(f"Unexpected artifact path: {name}")
        threshold = float(item["selected_threshold"])
        if not np.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError(f"Invalid frozen threshold: {name}")
        specs.append({"model": name, "artifact": str(artifact.relative_to(root)).replace("\\", "/"),
                      "threshold": threshold, "threshold_source": "saved_validation_calibration"})
    for name in ("logistic_regression_f0", "random_forest_f0"):
        specs.append({"model": name, "artifact": f"models/creditcard/{name}.joblib",
                      "threshold": 0.5, "threshold_source": "fixed_default_0.50_no_saved_F0_calibration"})
    inputs = [calibration_path, root / "data/processed/creditcard_split_metadata.json",
              root / "data/processed/creditcard_leakage_audit.json",
              root / "data/processed/creditcard_feature_metadata.json",
              root / "data/processed/creditcard_test_features.parquet", Path(__file__).resolve()]
    inputs.extend(root / spec["artifact"] for spec in specs)
    # Record earlier test-bearing evidence without using its test metrics to choose models.
    imbalance = root / "reports/models/creditcard_imbalance_f1.json"
    if imbalance.exists():
        inputs.append(imbalance)
    return specs, inputs


def render_table(rows: list[dict]) -> str:
    lines = ["| Model | Threshold | PR-AUC (AP) | ROC-AUC | F1 | Recall | False alarms / 1k legitimate | TP | FP | FN | TN |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['model']} | {row['threshold']:.2f} | {row['pr_auc_ap']:.6f} | {row['roc_auc']:.6f} | {row['f1']:.6f} | {row['recall']:.6f} | {row['false_alarms_per_1000_legitimate']:.6f} | {row['tp']} | {row['fp']} | {row['fn']} | {row['tn']} |")
    return "\n".join(lines)


def run(root: Path = ROOT) -> dict:
    output = root / "reports/final"
    if output.exists():
        raise FileExistsError("Final evaluation directory already exists; use saved results. Do not rescore.")
    specs, inputs = frozen_spec(root)
    hashes = {str(path.relative_to(root)).replace("\\", "/"): file_hash(path) for path in inputs}
    bundles = {}
    for spec in specs:
        bundle = joblib.load(root / spec["artifact"])
        if not bundle.get("features") or not hasattr(bundle.get("model"), "predict_proba"):
            raise ValueError(f"Incomplete model bundle: {spec['model']}")
        if list(bundle["model"].classes_) != [0, 1]:
            raise ValueError("Positive-class probability must be column 1")
        spec["features"] = list(bundle["features"])
        bundles[spec["model"]] = bundle
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "one prediction pass per listed frozen artifact; no fitting, resampling, threshold search or model selection",
        "untouched_test_claim_supported": False,
        "prior_exposure": ["threshold calibration report already contains test confusion metrics",
                           "imbalance comparison code evaluates test during development",
                           "replay service reads the same test partition; historical usage is not fully logged"],
        "models": specs, "input_sha256": hashes,
        "environment": {"python": platform.python_version(), **{name: version(name) for name in ("numpy", "pandas", "scikit-learn", "joblib", "xgboost")}},
    }
    output.mkdir()  # Exclusive acquisition; never overwrite or automatically retry.
    receipt_path = output / "receipt.json"
    receipt_path.write_text(json.dumps({"status": "started", "created_utc": manifest["created_utc"]}, indent=2), encoding="utf-8")
    (output / "frozen_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    metadata = json.loads((root / "data/processed/creditcard_split_metadata.json").read_text(encoding="utf-8"))
    audit = json.loads((root / "data/processed/creditcard_leakage_audit.json").read_text(encoding="utf-8"))
    if not all(audit["split_order_check"].values()) or metadata["scaler_fit_split"] != "train":
        raise ValueError("Chronological leakage checks failed")
    boundaries = metadata["splits"]
    if not boundaries["train"]["max_time"] < boundaries["validation"]["min_time"] <= boundaries["validation"]["max_time"] < boundaries["test"]["min_time"]:
        raise ValueError("Split metadata overlaps")
    test = pd.read_parquet(root / "data/processed/creditcard_test_features.parquet")
    expected = boundaries["test"]
    if not test["Time"].is_monotonic_increasing or len(test) != expected["rows"] or test["Class"].sum() != expected["fraud_count"] or test["Time"].min() != expected["min_time"] or test["Time"].max() != expected["max_time"]:
        raise ValueError("Test content does not match chronological split metadata")
    y = test["Class"].to_numpy()
    rows, predictions = [], {"labels": y, "time": test["Time"].to_numpy()}
    for spec in specs:
        bundle = bundles[spec["model"]]
        features = bundle["features"]
        scores = np.asarray(bundle["model"].predict_proba(test[features]))[:, 1]
        rows.append({"model": spec["model"], "feature_count": len(features),
                     "threshold_source": spec["threshold_source"], **evaluate(y, scores, spec["threshold"])})
        predictions[spec["model"]] = scores
        print(f"Scored {spec['model']}", flush=True)
    # Detect any concurrent mutation of the frozen inputs before committing results.
    if any(file_hash(root / relative) != digest for relative, digest in hashes.items()):
        raise RuntimeError("Frozen input changed during evaluation")
    result = {"created_utc": manifest["created_utc"], "untouched_test_claim_supported": False,
              "split_metadata": boundaries, "test_rows": len(y), "test_fraud_count": int(y.sum()),
              "metric_definitions": {"pr_auc_ap": "sklearn average_precision_score (step-weighted AP, not trapezoidal PR area)",
                                     "false_alarms_per_1000_legitimate": "1000 * FP / (TN + FP)",
                                     "false_alarms_per_1000_all": "1000 * FP / all test rows",
                                     "classification": "probability >= saved threshold"}, "models": rows}
    (output / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(output / "metrics.csv", index=False)
    np.savez_compressed(output / "predictions.npz", **predictions)
    markdown = f"# Final chronological test results\n\nPreviously exposed test partition; see the frozen manifest. Models and thresholds were fixed before this run.\n\n{len(y):,} transactions, {int(y.sum())} fraud cases. PR-AUC is average precision. False alarms / 1k uses legitimate transactions as its denominator.\n\n## F1 models: saved validation thresholds\n\n"
    markdown += render_table([row for row in rows if row["threshold_source"] == "saved_validation_calibration"])
    markdown += "\n\n## F0 baselines: fixed default threshold 0.50\n\n" + render_table([row for row in rows if row["threshold_source"] != "saved_validation_calibration"])
    markdown += "\n\nF0 and F1 are feature-set names; F1 in the metric column is the classification F1 score. Repeated model variants are reported as saved artifacts and are not independent experimental replications.\n"
    (output / "FINAL_TABLES.md").write_text(markdown, encoding="utf-8")
    receipt = {"status": "complete", "completed_utc": datetime.now(timezone.utc).isoformat(),
               "prediction_passes_per_artifact": 1,
               "output_sha256": {path.name: file_hash(path) for path in sorted(output.iterdir()) if path != receipt_path}}
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    run()
