"""Exploratory analysis for the Credit Card Fraud Detection dataset only."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def load_creditcard_data(path: str | Path = "data/creditcard.csv") -> pd.DataFrame:
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


if __name__ == "__main__":
    data = load_creditcard_data()
    print(summarize_creditcard(data).to_string())
    plot_creditcard_overview(data)
