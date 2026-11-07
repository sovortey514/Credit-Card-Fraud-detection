# Week 1–4 implementation record

## Week 1 — environment and reproducibility

- Git repository and project layout are present.
- Docker files are present in the project root.
- Pre-commit hooks are defined for Black and Flake8.
- The central seed and path configuration is in `src/fraud_detection/config.py`.

## Week 2 — literature and Cambodian context

The research proposal remains the source document for the literature review. NBC publications about Bakong and KHQR are treated as contextual sources, not transaction-level training data. Public NBC reports can support adoption, payment-system, and risk-context discussion; confidential transaction records would require formal permission and are not assumed to be available.

## Week 3 — data acquisition and EDA

Run the audit against every downloaded dataset:

```powershell
.\.venv\Scripts\python.exe -m src.fraud_detection.audit data/raw/paysim.csv data/raw/creditcard.csv
```

The audit records SHA-256 hashes, row counts, missing values, fraud prevalence, transaction-type counts, and amount skewness before and after a log transform.

## Week 4 — temporal split and leakage audit

Run the canonical PaySim pipeline:

```powershell
.\.venv\Scripts\python.exe -m src.fraud_detection.data_pipeline --data data/raw/paysim.csv
```

It keeps `TRANSFER` and `CASH_OUT`, excludes post-transaction balances, creates whole-time-step 70/15/15 partitions, writes Parquet files, and records hashes in `reports/data_provenance.json`.

The ULB dataset should use its transaction-time column for the same chronological split utility; it must not be randomly shuffled before evaluation.
