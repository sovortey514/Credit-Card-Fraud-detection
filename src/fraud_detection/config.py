"""Central reproducibility and data-processing configuration."""

from pathlib import Path
import random

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"
SEED = 42
TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
TRANSACTION_TYPES = ("TRANSFER", "CASH_OUT")


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
