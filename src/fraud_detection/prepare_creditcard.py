from hashlib import sha256
import json
from pathlib import Path

import pandas as pd
from sklearn.preprocessing import RobustScaler


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "raw" / "creditcard.csv"
OUTPUT = ROOT / "data" / "processed"
FEATURES = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
TARGET = "Class"


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Download the dataset first: {SOURCE}")

    columns = FEATURES + [TARGET]
    df = pd.read_csv(SOURCE, usecols=columns).sort_values("Time", kind="stable")
    if df[TARGET].nunique() != 2:
        raise ValueError("The dataset must contain both legitimate and fraud classes.")

    duplicate_count = int(df.duplicated().sum())
    df = df.drop_duplicates(keep="first").reset_index(drop=True)

    boundaries = df["Time"].quantile([0.70, 0.85]).tolist()
    train = df[df["Time"] <= boundaries[0]].copy()
    validation = df[(df["Time"] > boundaries[0]) & (df["Time"] <= boundaries[1])].copy()
    test = df[df["Time"] > boundaries[1]].copy()
    splits = {"train": train, "validation": validation, "test": test}

    if any(part.empty or part[TARGET].nunique() < 2 for part in splits.values()):
        raise ValueError("Each chronological split must contain both classes.")

    amount_scaler = RobustScaler().fit(train[["Amount"]])
    time_scaler = RobustScaler().fit(train[["Time"]])
    for part in splits.values():
        part["scaled_amount"] = amount_scaler.transform(part[["Amount"]]).ravel()
        part["scaled_time"] = time_scaler.transform(part[["Time"]]).ravel()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, part in splits.items():
        part.to_parquet(OUTPUT / f"creditcard_{name}.parquet", index=False)

    source_hash = file_sha256(SOURCE)
    train_max = float(train["Time"].max())
    validation_min = float(validation["Time"].min())
    validation_max = float(validation["Time"].max())
    test_min = float(test["Time"].min())
    audit = {
        "source_dataset": SOURCE.name,
        "source_sha256": source_hash,
        "duplicate_rows_removed": duplicate_count,
        "split_order_check": {
            "train_max_time_lt_validation_min_time": train_max < validation_min,
            "validation_max_time_lt_test_min_time": validation_max < test_min,
            "no_future_to_past_overlap": train_max < validation_min < test_min,
        },
        "preprocessing_check": {
            "scaler_fit_split": "train",
            "scaled_columns": ["Amount", "Time"],
            "validation_and_test_only_transformed": True,
        },
    }
    (OUTPUT / "creditcard_leakage_audit.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )

    metadata = {
        "source_dataset": SOURCE.name,
        "source_sha256": source_hash,
        "target": TARGET,
        "duplicate_rows_removed": duplicate_count,
        "features": FEATURES,
        "scaled_features": ["scaled_amount", "scaled_time"],
        "split_strategy": "chronological by Time",
        "scaler_fit_split": "train",
        "splits": {
            name: {
                "rows": len(part),
                "fraud_count": int(part[TARGET].sum()),
                "fraud_rate_percent": float(part[TARGET].mean() * 100),
                "min_time": float(part["Time"].min()),
                "max_time": float(part["Time"].max()),
            }
            for name, part in splits.items()
        },
    }
    (OUTPUT / "creditcard_split_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
