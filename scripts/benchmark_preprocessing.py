"""Benchmark serialized credit-card preprocessing latency."""

from pathlib import Path
import sys
from time import perf_counter

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PIPELINE_PATH = ROOT / "models" / "creditcard_preprocessing.joblib"
TEST_PATH = ROOT / "data" / "processed" / "creditcard_test.parquet"


def main() -> None:
    pipeline = joblib.load(PIPELINE_PATH)
    sample = pd.read_parquet(TEST_PATH).head(1_000)
    started = perf_counter()
    pipeline.transform(sample)
    elapsed_ms = (perf_counter() - started) * 1_000
    per_transaction_ms = elapsed_ms / len(sample)
    print(f"Transactions: {len(sample)}")
    print(f"Batch elapsed: {elapsed_ms:.3f} ms")
    print(f"Per transaction: {per_transaction_ms:.6f} ms")
    if per_transaction_ms >= 2:
        raise SystemExit("Preprocessing latency target missed: expected < 2 ms per transaction")


if __name__ == "__main__":
    main()
