"""Replay the held-out credit-card test set in chronological order."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.schemas.replay import ReplaySpeed
from app.services.model_service import CreditCardModelService
from app.services.replay_service import CreditCardReplayService


async def replay(speed: ReplaySpeed, model: str, limit: int | None, verify: bool) -> None:
    service = CreditCardReplayService(CreditCardModelService())
    expected_sequence = 0
    emitted = 0
    async for event in service.events(speed, model, limit):
        if event.sequence != expected_sequence:
            raise RuntimeError(f"Dropped or reordered event: expected {expected_sequence}, received {event.sequence}")
        print(json.dumps(event.model_dump()), flush=True)
        expected_sequence += 1
        emitted += 1
    if verify:
        print(json.dumps({"replayed": emitted, "expected": expected_sequence, "dropped": 0, "ordered": True}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--speed", type=int, choices=(10, 50, 100, 250), default=10)
    parser.add_argument("--model", choices=("xgboost", "random_forest"), default="xgboost")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    asyncio.run(replay(args.speed, args.model, args.limit, args.verify))


if __name__ == "__main__":
    main()
