"""Pydantic schemas for the 30-field ULB credit-card transaction payload."""

from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class CreditCardTransaction(BaseModel):
    """One raw transaction: Time, Amount, and V1-V28 PCA components."""

    model_config = ConfigDict(extra="forbid")

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
        return pd.DataFrame([self.model_dump()])


class PredictionResponse(BaseModel):
    model: Literal["xgboost", "random_forest"]
    fraud_probability: float
    is_fraud: bool
    threshold: float


class SHAPContribution(BaseModel):
    feature: str
    value: float
    direction: Literal["increases_risk", "decreases_risk"]


class ExplanationResponse(PredictionResponse):
    base_value: float
    top_contributions: list[SHAPContribution]
