"""Exploratory analysis for the Credit Card Fraud Detection dataset only."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


PCA_COMPONENTS = [f"V{i}" for i in range(1, 29)]


def load_creditcard_data(path: str | Path = "data/raw/creditcard.csv") -> pd.DataFrame:
    """Load and validate ``creditcard.csv``."""
    frame = pd.read_csv(path)
    required = {"Time", "Amount", "Class"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing credit-card columns: {sorted(missing)}")
    return frame


def summarize_creditcard(frame: pd.DataFrame) -> pd.Series:
    """Return basic class-balance statistics."""
    fraud = int(frame["Class"].sum())
    total = len(frame)
    return pd.Series({
        "transactions": total,
        "legitimate": total - fraud,
        "fraud": fraud,
        "fraud_rate_percent": fraud / total * 100 if total else 0.0,
    })


def plot_creditcard_overview(frame: pd.DataFrame) -> None:
    """Plot class balance and transaction amounts."""
    sns.set_theme(style="whitegrid")
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    sns.countplot(data=frame, x="Class", hue="Class", legend=False, palette={0: "#10B981", 1: "#EF4444"}, ax=axes[0])
    axes[0].set_title("Credit-card class balance")
    axes[0].set_xlabel("Class (0 = legitimate, 1 = fraud)")
    sns.histplot(data=frame, x="Amount", hue="Class", bins=50, element="step", stat="density", common_norm=False, ax=axes[1])
    axes[1].set_title("Transaction amount distribution")
    figure.tight_layout()
    plt.show()


def generate_extended_eda(frame: pd.DataFrame, output_dir: Path) -> dict[str, object]:
    """Save reusable EDA plots and a summary for the thesis workflow."""
    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    overview, axes = plt.subplots(1, 2, figsize=(13, 5))
    sns.countplot(data=frame, x="Class", hue="Class", legend=False,
                  palette={0: "#10B981", 1: "#EF4444"}, ax=axes[0])
    axes[0].set_title("Credit-card class balance")
    axes[0].set_xlabel("Class (0 = legitimate, 1 = fraud)")
    axes[0].set_ylabel("Transactions")
    axes[0].set_yscale("log")
    sns.histplot(data=frame, x="Amount", hue="Class", bins=60,
                 element="step", stat="density", common_norm=False, ax=axes[1])
    axes[1].set_title("Transaction amount distribution")
    axes[1].set_xlabel("Amount")
    overview.tight_layout()
    overview.savefig(output_dir / "creditcard_eda_overview.png", dpi=160)
    plt.close(overview)

    time_figure, time_axis = plt.subplots(figsize=(11, 5))
    sns.histplot(data=frame, x="Time", hue="Class", bins=48,
                 element="step", stat="count", common_norm=False, ax=time_axis)
    time_axis.set_title("Transaction timing across the approximately 48-hour window")
    time_axis.set_xlabel("Seconds elapsed")
    time_axis.set_ylabel("Transactions")
    time_figure.tight_layout()
    time_figure.savefig(output_dir / "creditcard_time_distribution.png", dpi=160)
    plt.close(time_figure)

    # A fixed sample keeps the 28-panel visualization responsive; summary
    # statistics below still use every row in the dataset.
    pca_frame = frame.sample(n=min(50_000, len(frame)), random_state=42)
    pca_figure, pca_axes = plt.subplots(7, 4, figsize=(16, 22))
    for axis, feature in zip(pca_axes.flat, PCA_COMPONENTS):
        sns.histplot(data=pca_frame, x=feature, bins=40, color="#2563EB", ax=axis)
        axis.set_title(feature)
        axis.set_xlabel("")
        axis.set_ylabel("")
    pca_figure.suptitle("Distributions of anonymized PCA features V1–V28", y=0.995)
    pca_figure.tight_layout()
    pca_figure.savefig(output_dir / "creditcard_pca_distributions.png", dpi=160)
    plt.close(pca_figure)

    fraud = int(frame["Class"].sum())
    summary = {
        "transactions": len(frame),
        "legitimate": len(frame) - fraud,
        "fraud": fraud,
        "fraud_rate_percent": fraud / len(frame) * 100,
        "missing_cells": int(frame.isna().sum().sum()),
        "duplicate_rows": int(frame.duplicated().sum()),
        "time_min_seconds": float(frame["Time"].min()),
        "time_max_seconds": float(frame["Time"].max()),
        "time_span_hours": float((frame["Time"].max() - frame["Time"].min()) / 3600),
        "amount_skewness": float(frame["Amount"].skew()),
        "pca_components": PCA_COMPONENTS,
        "plots": [
            "creditcard_eda_overview.png",
            "creditcard_time_distribution.png",
            "creditcard_pca_distributions.png",
        ],
    }
    (output_dir / "creditcard_eda_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/creditcard.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/eda"))
    args = parser.parse_args()
    print(json.dumps(generate_extended_eda(load_creditcard_data(args.data), args.output_dir), indent=2))
