"""Chronological held-out credit-card replay and delivery accounting."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import time
from typing import AsyncIterator, Iterator

import pandas as pd

from app.schemas.creditcard import CreditCardTransaction
from app.schemas.replay import ReplayEvent, ReplaySpeed
from app.services.model_service import CreditCardModelService

ROOT = Path(__file__).resolve().parents[2]
TEST_PATH = ROOT / "data" / "processed" / "creditcard_test.parquet"
ALLOWED_SPEEDS = (10, 50, 100, 250)
RAW_COLUMNS = ["Time", "Amount", *[f"V{i}" for i in range(1, 29)]]


class CreditCardReplayService:
    """Replay held-out transactions in Time order and score each event."""

    def __init__(self, model_service: CreditCardModelService) -> None:
        self.model_service = model_service

    def transactions(self, limit: int | None = None) -> Iterator[CreditCardTransaction]:
        frame = pd.read_parquet(TEST_PATH).sort_values("Time", kind="stable")
        if limit is not None:
            frame = frame.head(limit)
        for row in frame[RAW_COLUMNS].to_dict(orient="records"):
            yield CreditCardTransaction.model_validate(row)

    def score(self, transaction: CreditCardTransaction, sequence: int, model_name: str) -> ReplayEvent:
        started = time.perf_counter()
        prediction = self.model_service.predict(transaction, model_name)
        return ReplayEvent(
            sequence=sequence,
            time_seconds=transaction.Time,
            amount=transaction.Amount,
            model=model_name,
            fraud_probability=prediction.fraud_probability,
            is_fraud=prediction.is_fraud,
            threshold=prediction.threshold,
            latency_ms=(time.perf_counter() - started) * 1000,
            pca_features={name: float(getattr(transaction, name)) for name in ("V14", "V17", "V12", "V10")},
        )

    async def events(
        self,
        speed: ReplaySpeed,
        model_name: str,
        limit: int | None = None,
    ) -> AsyncIterator[ReplayEvent]:
        delay = 1.0 / speed
        for sequence, transaction in enumerate(self.transactions(limit)):
            yield self.score(transaction, sequence, model_name)
            await asyncio.sleep(delay)


def sse_message(event: ReplayEvent) -> str:
    return f"id: {event.sequence}\nevent: scored\ndata: {json.dumps(event.model_dump())}\n\n"
