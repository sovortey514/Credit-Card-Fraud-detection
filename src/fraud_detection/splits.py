"""Leakage-safe chronological split utilities shared by all pipelines."""

import pandas as pd

from .config import TRAIN_RATIO, VALIDATION_RATIO


def chronological_split(df, time_column="step", train_ratio=TRAIN_RATIO,
                        validation_ratio=VALIDATION_RATIO):
    """Split by whole time steps, targeting 70/15/15 without future overlap."""
    if train_ratio <= 0 or validation_ratio <= 0 or train_ratio + validation_ratio >= 1:
        raise ValueError("Invalid chronological split ratios.")
    if time_column not in df or df[time_column].nunique() < 3:
        raise ValueError("At least three distinct time steps are required.")
    ordered = df.sort_values(time_column, kind="stable").reset_index(drop=True)
    counts = ordered.groupby(time_column, sort=True).size().cumsum()
    total = len(ordered)
    train_end = counts.sub(total * train_ratio).abs().idxmin()
    validation_end = counts.sub(total * (train_ratio + validation_ratio)).abs().idxmin()
    train = ordered[ordered[time_column] <= train_end].copy()
    validation = ordered[(ordered[time_column] > train_end) &
                         (ordered[time_column] <= validation_end)].copy()
    test = ordered[ordered[time_column] > validation_end].copy()
    parts = {"train": train, "validation": validation, "test": test}
    if any(part.empty for part in parts.values()):
        raise ValueError("One or more chronological partitions are empty.")
    if not (train[time_column].max() < validation[time_column].min() <
            test[time_column].min()):
        raise ValueError("Chronological partitions overlap or are out of order.")
    return parts
