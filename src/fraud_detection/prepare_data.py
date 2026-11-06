
from pathlib import Path
import pandas as pd
import numpy as np
import json

# =====================================================
# 1. PROJECT PATHS
# =====================================================

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

csv_files = list(RAW_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError(
        "No CSV file found in data/raw/"
    )

source = csv_files[0]

print("=" * 60)
print("MONEY TRANSFER FRAUD DETECTION")
print("DATA PREPARATION")
print("=" * 60)

print(f"\nDataset: {source.name}")

# =====================================================
# 2. LOAD TRANSFER TRANSACTIONS
# =====================================================

print("\n[1/5] Loading TRANSFER transactions...")

columns = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "isFraud"
]

chunks = []

for chunk in pd.read_csv(
    source,
    usecols=columns,
    chunksize=200_000
):
    transfers = chunk.loc[
        chunk["type"] == "TRANSFER"
    ].copy()

    if not transfers.empty:
        chunks.append(transfers)

if not chunks:
    raise ValueError(
        "No TRANSFER transactions found."
    )

df = pd.concat(chunks, ignore_index=True)

df = df.sort_values(
    "step",
    kind="stable"
).reset_index(drop=True)

print(f"Total transfers: {len(df):,}")
print(f"Fraud transfers: {df['isFraud'].sum():,}")
print(
    f"Fraud rate: "
    f"{df['isFraud'].mean() * 100:.4f}%"
)

# =====================================================
# 3. FEATURE ENGINEERING
# =====================================================

print("\n[2/5] Creating features...")

df["log_amount"] = np.log1p(
    df["amount"]
)

df["log_oldbalanceOrg"] = np.log1p(
    df["oldbalanceOrg"]
)

# These are candidate pre-transaction features.
# Post-transaction balances and isFlaggedFraud
# are deliberately excluded.

print("Features created successfully.")

# =====================================================
# 4. CHRONOLOGICAL DATA SPLITTING
# =====================================================

print("\n[3/5] Splitting dataset chronologically...")

# Cumulative transaction counts per time step
step_counts = (
    df.groupby("step", sort=True)
    .size()
    .cumsum()
)

total = len(df)

# Approximate 70%, 15%, 15% by transaction count.
# Keep all rows of the same step in one partition.

train_end_step = int(
    (step_counts - total * 0.70)
    .abs()
    .idxmin()
)

val_end_step = int(
    (step_counts - total * 0.85)
    .abs()
    .idxmin()
)

if train_end_step >= val_end_step:
    raise ValueError(
        "Invalid chronological split boundaries."
    )

train = df[
    df["step"] <= train_end_step
].copy()

validation = df[
    (df["step"] > train_end_step)
    & (df["step"] <= val_end_step)
].copy()

test = df[
    df["step"] > val_end_step
].copy()

print(f"Training ends at step: {train_end_step}")
print(f"Validation ends at step: {val_end_step}")

# =====================================================
# 5. VALIDATE DATA SPLITS
# =====================================================

print("\n[4/5] Validating data splits...")

datasets = {
    "train": train,
    "validation": validation,
    "test": test
}

if any(dataset.empty for dataset in datasets.values()):
    raise ValueError(
        "One or more datasets are empty."
    )

assert len(train) + len(validation) + len(test) == total

assert train["step"].max() < validation["step"].min()
assert validation["step"].max() < test["step"].min()

assert (
    sum(int(d["isFraud"].sum()) for d in datasets.values())
    == int(df["isFraud"].sum())
)

for name, dataset in datasets.items():
    fraud_count = int(dataset["isFraud"].sum())

    if fraud_count == 0:
        raise ValueError(
            f"No fraud examples in {name} split."
        )

    print(
        f"{name.upper():12} | "
        f"Rows: {len(dataset):>8,} | "
        f"Share: {len(dataset)/total*100:>6.2f}% | "
        f"Fraud: {fraud_count:>5,} | "
        f"Fraud rate: {dataset['isFraud'].mean()*100:.4f}% | "
        f"Steps: {dataset['step'].min()}-"
        f"{dataset['step'].max()}"
    )

# =====================================================
# 6. SAVE DATASETS
# =====================================================

print("\n[5/5] Saving processed datasets...")

for name, dataset in datasets.items():

    output_file = OUTPUT_DIR / f"{name}.csv"

    dataset.to_csv(
        output_file,
        index=False
    )

    print(f"Saved: {output_file.name}")

# Save split metadata for reproducibility
metadata = {
    "source_dataset": source.name,
    "transaction_type": "TRANSFER",
    "total_transactions": total,
    "train_end_step": train_end_step,
    "validation_end_step": val_end_step,
    "features": [
        "step",
        "amount",
        "oldbalanceOrg",
        "log_amount",
        "log_oldbalanceOrg"
    ],
    "splits": {
        name: {
            "transactions": len(dataset),
            "fraud_count": int(dataset["isFraud"].sum()),
            "fraud_rate_percent": round(
                float(dataset["isFraud"].mean() * 100),
                6
            ),
            "min_step": int(dataset["step"].min()),
            "max_step": int(dataset["step"].max())
        }
        for name, dataset in datasets.items()
    }
}

metadata_file = OUTPUT_DIR / "split_metadata.json"

with open(metadata_file, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=4)

print(f"Saved: {metadata_file.name}")

print("\n" + "=" * 60)
print("DATA PREPARATION COMPLETED SUCCESSFULLY!")
print("=" * 60)
