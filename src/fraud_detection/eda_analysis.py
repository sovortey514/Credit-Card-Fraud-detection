from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "raw"
REPORT_DIR = ROOT / "reports" / "eda"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

csv_files = list(DATA_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError("PaySim CSV not found in data/raw")

DATASET_PATH = csv_files[0]

print("Loading PaySim dataset...")
df = pd.read_csv(DATASET_PATH)

print("\n===== DATASET INFORMATION =====")
print("Total transactions:", len(df))
print("Total columns:", len(df.columns))

print("\n===== FRAUD DISTRIBUTION =====")
fraud_counts = df["isFraud"].value_counts().sort_index()
print(fraud_counts)

fraud_rate = df["isFraud"].mean() * 100
print(f"Fraud percentage: {fraud_rate:.4f}%")

print("\n===== TRANSACTION TYPES =====")
type_summary = (
    df.groupby("type")
    .agg(total=("isFraud", "size"), fraud=("isFraud", "sum"))
    .reset_index()
)

type_summary["fraud_rate_percent"] = type_summary["fraud"] / type_summary["total"] * 100

print(type_summary.to_string(index=False))

print("\n===== MISSING VALUES =====")
missing = df.isnull().sum()
print(missing)

print("\n===== AMOUNT STATISTICS =====")
print(df["amount"].describe())

# Save research results
type_summary.to_csv(REPORT_DIR / "transaction_type_summary.csv", index=False)

missing.to_csv(REPORT_DIR / "missing_values.csv", header=["missing_count"])

pd.DataFrame(
    {
        "metric": [
            "total_transactions",
            "fraud_transactions",
            "legitimate_transactions",
            "fraud_rate_percent",
        ],
        "value": [
            len(df),
            int(df["isFraud"].sum()),
            int((df["isFraud"] == 0).sum()),
            fraud_rate,
        ],
    }
).to_csv(REPORT_DIR / "dataset_summary.csv", index=False)

# Fraud distribution chart
fig, ax = plt.subplots(figsize=(7, 5))
fraud_counts.plot(kind="bar", ax=ax)

ax.set_title("PaySim Fraud Distribution")
ax.set_xlabel("Fraud Label (0 = Normal, 1 = Fraud)")
ax.set_ylabel("Number of Transactions")

plt.tight_layout()
plt.savefig(REPORT_DIR / "fraud_distribution.png", dpi=150)
plt.close()

print("\nEDA completed successfully!")
print(f"Reports saved to: {REPORT_DIR}")
