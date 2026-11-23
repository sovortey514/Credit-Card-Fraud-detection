"""Stateful deterministic risk rules used alongside the ML score."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Lock


WINDOWS = (60, 600, 3600)


@dataclass
class _EntityState:
    transactions: deque[tuple[float, float]] = field(default_factory=deque)


class RiskEngine:
    """Evaluate short-window velocity and amount-anomaly rules in memory.

    The in-memory store is suitable for the local prototype. Production deployments
    can replace this class with a Redis-backed implementation without changing the
    API response contract.
    """

    def __init__(self, low_threshold: float = 0.25) -> None:
        self.low_threshold = low_threshold
        self._states: dict[str, _EntityState] = {}
        self._lock = Lock()

    def evaluate(
        self,
        *,
        entity_key: str,
        timestamp: float,
        amount: float,
        ml_probability: float,
        ml_threshold: float,
        commit: bool = True,
    ) -> dict[str, object]:
        with self._lock:
            state = self._states.setdefault(entity_key, _EntityState())
            previous = list(state.transactions)
            if commit:
                state.transactions.append((float(timestamp), float(amount)))
                self._trim(state.transactions, timestamp)

        triggered: list[dict[str, object]] = []
        count_60 = self._count(previous, timestamp, 60)
        if count_60 + 1 > 3:
            triggered.append({
                "code": "velocity_60s",
                "message": f"More than 3 transactions in 60 seconds ({count_60 + 1})",
                "severity": "high",
            })

        prior_amounts = [value for time_value, value in previous if timestamp - time_value <= 3600]
        if prior_amounts:
            rolling_average = sum(prior_amounts) / len(prior_amounts)
            if rolling_average > 0 and amount > 5 * rolling_average:
                triggered.append({
                    "code": "amount_spike",
                    "message": f"Amount is more than 5x the rolling average (${rolling_average:.2f})",
                    "severity": "medium",
                })
        else:
            rolling_average = 0.0

        hard_rule = any(rule["severity"] == "high" for rule in triggered)
        if hard_rule or ml_probability >= ml_threshold:
            route = "flag"
        elif ml_probability >= self.low_threshold or triggered:
            route = "step_up"
        else:
            route = "approve"

        return {
            "route": route,
            "triggered_rules": triggered,
            "velocity": {
                "count_1m": self._count(previous, timestamp, 60) + (1 if commit else 0),
                "count_10m": self._count(previous, timestamp, 600) + (1 if commit else 0),
                "count_1h": self._count(previous, timestamp, 3600) + (1 if commit else 0),
                "spend_1m": self._spend(previous, timestamp, 60) + (amount if commit else 0),
                "spend_10m": self._spend(previous, timestamp, 600) + (amount if commit else 0),
                "spend_1h": self._spend(previous, timestamp, 3600) + (amount if commit else 0),
                "rolling_average_amount_1h": rolling_average,
            },
        }

    @staticmethod
    def _trim(events: deque[tuple[float, float]], timestamp: float) -> None:
        while events and timestamp - events[0][0] > WINDOWS[-1]:
            events.popleft()

    @staticmethod
    def _count(events: list[tuple[float, float]] | deque[tuple[float, float]], timestamp: float, window: int) -> int:
        return sum(1 for event_time, _ in events if 0 <= timestamp - event_time <= window)

    @staticmethod
    def _spend(events: list[tuple[float, float]] | deque[tuple[float, float]], timestamp: float, window: int) -> float:
        return sum(amount for event_time, amount in events if 0 <= timestamp - event_time <= window)
