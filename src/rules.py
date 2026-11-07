"""Fast, explainable first-tier rules for credit-card transactions."""

from __future__ import annotations

from typing import Any


def evaluate_rules(transaction: dict[str, Any]) -> tuple[bool, list[str]]:
    """Stage 1: check static security rules before ML scoring."""
    flags: list[str] = []
    amount = float(transaction.get("Amount", 0))
    hour = float(transaction.get("hour_of_day", 12))

    if amount > 5000:
        flags.append("CRITICAL_HIGH_AMOUNT")

    if (hour >= 22 or hour <= 5) and amount > 1000:
        flags.append("HIGH_RISK_NIGHT_TRANSACTION")

    if transaction.get("is_blacklisted_device", 0) == 1:
        flags.append("BLACKLISTED_DEVICE_ID")

    return len(flags) > 0, flags