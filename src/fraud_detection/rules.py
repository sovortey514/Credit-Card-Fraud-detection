"""Simple, explainable first-stage rules for credit-card transactions."""

from __future__ import annotations

import pandas as pd


def apply_rules(
    frame: pd.DataFrame,
    *,
    amount_threshold: float = 1_000.0,
) -> pd.DataFrame:
    """Return rule scores without using the target column.

    Rules are deliberately conservative: they are an alerting layer, not the
    final fraud decision. The model should still score every transaction.
    """
    required = {"Amount"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    result = frame.copy()
    result["rule_high_amount"] = (
        pd.to_numeric(result["Amount"], errors="coerce") >= amount_threshold
    ).astype(int)
    result["rule_score"] = result["rule_high_amount"]
    result["rule_flag"] = (result["rule_score"] > 0).astype(int)
    return result
