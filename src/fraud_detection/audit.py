"""Reproducible dataset audit for Week 3 evidence."""

import argparse
import json
from pathlib import Path

import pandas as pd

from .config import REPORTS_DIR, TRANSACTION_TYPES
from .provenance import sha256_file


def audit_dataset(path: Path) -> dict:
    frame = pd.read_csv(path)
    result = {
        "file": path.name,
        "sha256": sha256_file(path),
        "rows": len(frame),
        "columns": list(frame.columns),
        "missing_cells": int(frame.isna().sum().sum()),
    }
    if "isFraud" in frame:
        result["fraud_count"] = int(frame["isFraud"].sum())
        result["fraud_rate"] = float(frame["isFraud"].mean())
    if "type" in frame:
        result["transaction_types"] = frame["type"].value_counts().to_dict()
        result["fraud_by_type"] = frame.groupby("type")["isFraud"].sum().to_dict()
        result["pay_sim_types_used"] = list(TRANSACTION_TYPES)
    if "amount" in frame:
        result["amount_skewness"] = float(frame["amount"].skew())
        result["log_amount_skewness"] = float(frame["amount"].clip(lower=0).add(1).apply(__import__("numpy").log).skew())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    report = {path.stem: audit_dataset(path) for path in args.paths}
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    destination = REPORTS_DIR / "dataset_audit.json"
    destination.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
