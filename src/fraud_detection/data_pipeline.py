"""Canonical Week 3–4 PaySim data pipeline.

Run with: python -m src.fraud_detection.data_pipeline --data data/raw/paysim.csv
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import PROCESSED_DIR, REPORTS_DIR, SEED, TRANSACTION_TYPES
from .provenance import sha256_file
from .splits import chronological_split

REQUIRED = ["step", "type", "amount", "oldbalanceOrg", "isFraud"]
POST_TRANSACTION = {"newbalanceOrig", "newbalanceDest", "isFlaggedFraud"}


def load_dataset(path: Path) -> pd.DataFrame:
    """Load only pre-transaction fields and retain both fraud-bearing types."""
    available = pd.read_csv(path, nrows=0).columns.tolist()
    missing = set(REQUIRED) - set(available)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    frame = pd.read_csv(path, usecols=REQUIRED)
    return frame[frame["type"].isin(TRANSACTION_TYPES)].copy()


def prepare(path: Path, output_dir: Path = PROCESSED_DIR) -> dict:
    frame = load_dataset(path).sort_values("step", kind="stable").reset_index(drop=True)
    frame["log_amount"] = np.log1p(frame["amount"])
    frame["log_oldbalanceOrg"] = np.log1p(frame["oldbalanceOrg"])
    partitions = chronological_split(frame)
    output_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, partition in partitions.items():
        destination = output_dir / f"{name}.parquet"
        partition.to_parquet(destination, index=False)
        hashes[name] = sha256_file(destination)
    metadata = {
        "seed": SEED,
        "source": path.name,
        "source_sha256": sha256_file(path),
        "transaction_types": list(TRANSACTION_TYPES),
        "excluded_post_transaction_columns": sorted(POST_TRANSACTION),
        "partitions": {
            name: {
                "rows": len(partition),
                "fraud_count": int(partition["isFraud"].sum()),
                "min_step": int(partition["step"].min()),
                "max_step": int(partition["step"].max()),
                "sha256": hashes[name],
            }
            for name, partition in partitions.items()
        },
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "data_provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/raw/paysim.csv"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.data), indent=2))


if __name__ == "__main__":
    main()
