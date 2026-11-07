"""Training-only resampling helpers for imbalanced fraud data."""

from __future__ import annotations

import pandas as pd
from imblearn.combine import SMOTETomek


def smote_tomek_resample(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.Series]:
    """Apply SMOTE plus Tomek Links to training data only.

    Validation and test data must never be passed to this function.
    """
    sampler = SMOTETomek(random_state=random_state)
    sampled_features, sampled_target = sampler.fit_resample(features, target)
    return (
        pd.DataFrame(sampled_features, columns=features.columns),
        pd.Series(sampled_target, name=target.name),
    )
