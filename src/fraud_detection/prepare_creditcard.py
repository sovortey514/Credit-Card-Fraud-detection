from pathlib import Path
import json
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "raw" / "creditcard.csv"
OUTPUT = ROOT / "data" / "processed_creditcard"
FEATURES = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
TARGET = "Class"


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Download the dataset first: {SOURCE}")

    columns = FEATURES + [TARGET]
    df = pd.read_csv(SOURCE, usecols=columns).sort_values("Time", kind="stable")
    if df[TARGET].nunique() != 2:
        raise ValueError("The dataset must contain both legitimate and fraud classes.")

    boundaries = df["Time"].quantile([0.70, 0.85]).tolist()
    train = df[df["Time"] <= boundaries[0]].copy()
    validation = df[(df["Time"] > boundaries[0]) & (df["Time"] <= boundaries[1])].copy()
    test = df[df["Time"] > boundaries[1]].copy()
    splits = {"train": train, "validation": validation, "test": test}

    if any(part.empty or part[TARGET].nunique() < 2 for part in splits.values()):
        raise ValueError("Each chronological split must contain both classes.")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, part in splits.items():
        part.to_csv(OUTPUT / f"{name}.csv", index=False)

    metadata = {
        "source_dataset": SOURCE.name,
        "target": TARGET,
        "features": FEATURES,
        "split_strategy": "chronological by Time",
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
    (OUTPUT / "split_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
