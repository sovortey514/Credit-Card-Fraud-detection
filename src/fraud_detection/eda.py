"""Command-line entry point for credit-card fraud EDA."""

import argparse
from pathlib import Path

from .creditcard_eda import load_creditcard_data, plot_creditcard_overview, summarize_creditcard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/creditcard.csv"))
    args = parser.parse_args()
    data = load_creditcard_data(args.data)
    print(summarize_creditcard(data).to_string())
    plot_creditcard_overview(data)


if __name__ == "__main__":
    main()
