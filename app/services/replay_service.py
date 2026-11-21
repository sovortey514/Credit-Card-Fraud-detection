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
ALLOWED_SPEEDS = (*range(1, 11), 50, 100, 250)
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

    def initial_history(self) -> pd.Series:
        frames = [
            pd.read_parquet(ROOT / "data" / "processed" / "creditcard_train.parquet"),
            pd.read_parquet(ROOT / "data" / "processed" / "creditcard_validation.parquet"),
        ]
        return pd.concat(frames, ignore_index=True).sort_values("Time", kind="stable")["Amount"].astype(float)

    def score(self, transaction: CreditCardTransaction, sequence: int, model_name: str, context_id: str = "replay") -> ReplayEvent:
        started = time.perf_counter()
        prediction = self.model_service.predict(transaction, model_name, context_id=context_id)
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
        context_id = f"replay-{id(asyncio.current_task())}"
        self.model_service.reset_history(context_id, self.initial_history().to_numpy())
        try:
            for sequence, transaction in enumerate(self.transactions(limit)):
                yield self.score(transaction, sequence, model_name, context_id)
                await asyncio.sleep(delay)
        finally:
            self.model_service.reset_history(context_id)


def sse_message(event: ReplayEvent) -> str:
    return f"id: {event.sequence}\nevent: scored\ndata: {json.dumps(event.model_dump())}\n\n"
