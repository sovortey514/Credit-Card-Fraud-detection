# Credit-card project implementation record

## Reproducibility and dataset

- Git repository and central project configuration are present.
- The raw ULB dataset is stored locally at `data/raw/creditcard.csv` and excluded from version control.
- Dataset checks cover row/class counts, missing values, duplicates, and SHA-256 provenance.
- The shared seed is defined in `src/fraud_detection/config.py`.

## Chronological preprocessing

- Rows are ordered by `Time`; exact duplicates are removed before splitting.
- Train, validation, and test partitions are chronological Parquet files in `data/processed/`.
- `RobustScaler` is fitted on training data only.
- Split boundaries and leakage checks are recorded in JSON metadata.

## Features and models

- F0 contains scaled `Time`, scaled `Amount`, and `V1`–`V28`.
- F1 adds cyclical time, amount statistics, and PCA-component interactions.
- Balanced Logistic Regression and Random Forest models are compared with five chronological folds.
- Validation PR and ROC curves are generated for the model/feature comparisons.

## Scope limitation

The ULB dataset has no explicit card-present/card-not-present indicator. The project can evaluate credit-card fraud on this dataset but cannot establish CNP-specific performance.
