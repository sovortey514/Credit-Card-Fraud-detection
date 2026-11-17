"""Plot the recorded chronological credit-card splits for the thesis."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data/processed/creditcard_split_metadata.json"
OUTPUT = ROOT / "reports/eda/creditcard_temporal_splits.png"


def main() -> None:
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    splits = metadata["splits"]
    names = ("train", "validation", "test")
    labels = ("Training", "Validation", "Test")
    rows = [splits[name]["rows"] for name in names]
    frauds = [splits[name]["fraud_count"] for name in names]
    total = sum(rows)
    colors = ("#32699b", "#299b95", "#8679ae")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), layout="constrained")
    fig.suptitle("Chronological partition: transaction volume and fraud", fontsize=15, weight="bold")
    for ax, values, title, ylabel in zip(
        axes, (rows, frauds), ("Transactions by split", "Fraud cases by split"),
        ("Transactions", "Fraud cases"),
    ):
        bars = ax.bar(labels, values, color=colors)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.set_ylim(0, max(values) * 1.23)
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
        for index, bar in enumerate(bars):
            rate = rows[index] / total * 100 if ax is axes[0] else frauds[index] / rows[index] * 100
            ax.annotate(f"{values[index]:,}\n({rate:.2f}%)", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 4), textcoords="offset points", ha="center", va="bottom")

    fig.text(0.5, -0.03, f"After removing {metadata['duplicate_rows_removed']:,} duplicate rows: {total:,} transactions. "
             "Left: share of deduplicated data; right: fraud rate within each split.", ha="center", fontsize=9)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
