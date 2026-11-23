"""Pydantic schemas for the 30-field ULB credit-card transaction payload."""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class CreditCardTransaction(BaseModel):
    """One raw transaction: Time, Amount, and V1-V28 PCA components."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str | None = Field(default=None, description="Optional upstream transaction identifier")
    account_id: str | None = Field(default=None, description="Optional account or customer key for velocity rules")
    card_id: str | None = Field(default=None, description="Optional card key for velocity rules")
    bin_country: str | None = None
    ip_country: str | None = None
    is_vpn_or_proxy: bool | None = None
    device_id: str | None = None

    Time: float = Field(..., description="Seconds elapsed since the first transaction")
    Amount: float = Field(..., ge=0, description="Transaction amount")
    V1: float
    V2: float
    V3: float
    V4: float
    V5: float
    V6: float
    V7: float
    V8: float
    V9: float
    V10: float
    V11: float
    V12: float
    V13: float
    V14: float
    V15: float
    V16: float
    V17: float
    V18: float
    V19: float
    V20: float
    V21: float
    V22: float
    V23: float
    V24: float
    V25: float
    V26: float
    V27: float
    V28: float

    def to_frame(self) -> pd.DataFrame:
        """Convert the validated payload to the raw model input frame."""
        return pd.DataFrame([{key: value for key, value in self.model_dump().items() if key not in {
            "transaction_id", "account_id", "card_id", "bin_country", "ip_country", "is_vpn_or_proxy", "device_id"
        }}])


class PredictionResponse(BaseModel):
    request_id: str
    model: Literal["xgboost", "random_forest"]
    fraud_probability: float
    is_fraud: bool
    threshold: float
    ml_probability: float
    route: Literal["approve", "step_up", "flag"]
    triggered_rules: list[dict[str, Any]] = Field(default_factory=list)
    velocity: dict[str, float | int] = Field(default_factory=dict)
    top_contributions: list["SHAPContribution"] = Field(default_factory=list)


class SHAPContribution(BaseModel):
    feature: str
    value: float
    direction: Literal["increases_risk", "decreases_risk"]


class ExplanationResponse(PredictionResponse):
    base_value: float
    top_contributions: list[SHAPContribution]


class AnalystDisposition(BaseModel):
    disposition: Literal["APPROVED", "CONFIRMED_FRAUD", "ESCALATED"]
    reviewer_id: str = Field(..., min_length=1, max_length=200)
    notes: str = Field(default="", max_length=2000)
