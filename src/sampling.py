"""Leakage-safe train/test splitting and imbalance handling."""

from __future__ import annotations

import pandas as pd
from imblearn.combine import SMOTETomek
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import TomekLinks
from sklearn.model_selection import train_test_split


def prepare_splits_and_resample(
    df: pd.DataFrame,
    target_col: str = "Class",
    test_size: float = 0.2,
    strategy: str = "smote",
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split first, then resample training data only.

    The test set is never passed to a resampler, preventing synthetic samples
    or Tomek-link filtering from leaking information into evaluation.
    """
    if target_col not in df.columns:
        raise ValueError(f"Target column not found: {target_col}")
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    if strategy not in {"smote", "tomek", "smote_tomek", "none"}:
        raise ValueError("strategy must be one of: smote, tomek, smote_tomek, none")

    x = df.drop(columns=[target_col])
    y = df[target_col]
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    print("--- Before Resampling (Train Set) ---")
    print(f"Normal (0): {(y_train == 0).sum():,}, Fraud (1): {(y_train == 1).sum():,}")

    if strategy == "smote":
        resampler = SMOTE(sampling_strategy=0.1, random_state=random_state)
    elif strategy == "tomek":
        resampler = TomekLinks()
    elif strategy == "smote_tomek":
        resampler = SMOTETomek(
            smote=SMOTE(sampling_strategy=0.1, random_state=random_state),
            random_state=random_state,
        )
    else:
        resampler = None

    if resampler is None:
        x_train_res, y_train_res = x_train, y_train
    else:
        x_train_res, y_train_res = resampler.fit_resample(x_train, y_train)
        x_train_res = pd.DataFrame(x_train_res, columns=x_train.columns)
        y_train_res = pd.Series(y_train_res, name=y_train.name)

    print("\n--- After Resampling (Train Set) ---")
    print(
        f"Normal (0): {(y_train_res == 0).sum():,}, "
        f"Fraud (1): {(y_train_res == 1).sum():,}"
    )
    print(
        f"Test Set Remains Untouched: {len(x_test):,} transactions "
        f"(Fraud: {(y_test == 1).sum():,})"
    )
    return x_train_res, x_test, y_train_res, y_test
