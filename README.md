# Credit Card Fraud Detection

Research and application code for imbalanced credit-card fraud detection using the Kaggle ULB dataset. It contains transaction time, amount, anonymized PCA components (`V1`–`V28`), and the `Class` label. The data does not identify card-present versus card-not-present transactions, so results cannot be described as a CNP-only evaluation.

## Requirements

- Windows 11, Python 3.12 (or the Python version supported by the selected environment), and Node.js 20+ for the dashboard.
- Place `creditcard.csv` at `data/raw/creditcard.csv`. The raw dataset is excluded from version control.

Create a Python 3.12 virtual environment and install the dependencies with
`python -m pip install -r requirements.txt -r requirements-data.txt`. Docker
Compose uses the same main requirements file. Copy `.env.example` to `.env` and
set `AUTH_JWT_SECRET` before running `docker compose up --build`.

The project-wide default random seed is `42` in
[`config.py`](src/fraud_detection/config.py); pass it explicitly to stochastic
estimators and searches. Exact results can still vary across library versions,
hardware, and parallel execution.

The requested project layout maps to `data/raw/`, `src/features/`,
`src/models/`, `api/`, `frontend/`, and `tests/`. Existing implementations
remain in `src/features.py`, `src/fraud_detection/`, and `app/api/`; trained
artifacts live in the ignored `models/` directory.

The [four-week literature protocol](docs/LITERATURE_REVIEW_PROTOCOL.md) and
[literature matrix](docs/LITERATURE_MATRIX.md) define the research workflow.

## Prepare the data

```powershell
.\.venv\Scripts\python.exe scripts/verify_data.py
.\.venv\Scripts\python.exe -m src.fraud_detection.eda
.\.venv\Scripts\python.exe -m src.fraud_detection.prepare_creditcard
.\.venv\Scripts\python.exe -m src.fraud_detection.diagram_preprocessing
```

Preparation sorts by time, removes duplicate rows, creates chronological train/validation/test partitions, fits scaling on training data only, and writes Parquet files and audit metadata under `data/processed/`.
For the separate feature contract, run `python -m src.fraud_detection.task5_features` after preparation. It writes F0 (30 columns) and F1 (F0 plus seven engineered columns) metadata and splits under `data/engineered_features/`. Rolling mean and population standard deviation use only the previous 1,000 rows, with zero when no previous row exists and stable input order for equal timestamps. The hour encoding is a phase relative to the dataset start. These files do not change historical models or their feature contract.

Run `python -m scripts.prepare_feature_contract` to fit and serialize the separate F0/F1 pipelines and benchmark single-row transformations. `POST /api/v1/features` accepts a transaction, `feature_set`, and optional `history` and `last_time`; pass the returned history and timestamp to the next chronological request. Start with empty history for a new stream, or supply the actual preceding amounts and timestamp for a later split. The endpoint is separate from existing prediction models and its history must be isolated by the caller. The local benchmark measures feature computation only, not HTTP or validation latency.
The diagram-aligned feature pipeline then saves engineered splits and its fitted preprocessor under `data/diagram_aligned/`.

## Fit preprocessing and compare models

**Legacy workflow:** the scripts below use the original research-feature datasets and existing model format. They do not train or evaluate the diagram-aligned dataset; update them and retrain models before using the new features for inference. Previously reported results and models are preserved as historical artifacts.

```powershell
.\.venv\Scripts\python.exe scripts/fit_creditcard_preprocessing.py
.\.venv\Scripts\python.exe scripts/benchmark_preprocessing.py
.\.venv\Scripts\python.exe scripts/compare_creditcard_models.py
```

The comparison trains balanced Logistic Regression and Random Forest baselines, evaluates F0/F1 with five chronological `TimeSeriesSplit` folds, and saves validation metrics plus PR/ROC plots under `reports/models/`.

## Run the API and dashboard

Start the credit-card scoring API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Start the authentication and user-management API in a second terminal. Configure
`AUTH_BOOTSTRAP_EMAIL` and `AUTH_BOOTSTRAP_PASSWORD` in `.env` before first use.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.standalone_user_api:app --reload --port 8001
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The API requires the trained model and preprocessing artifacts under `models/`. Docker Compose provides the local API and MySQL services.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Research limitation

The ULB dataset is anonymized and has no explicit payment-channel field. Findings apply to this dataset; they cannot establish CNP-specific performance or performance on real bank transactions.

## Final evaluation and thesis chapters

The [Week 18 record](docs/WEEK18_FINAL_EVALUATION.md) links the [final metric tables](reports/final/FINAL_TABLES.md), [Chapter 5: Empirical Results](docs/CHAPTER_5_EMPIRICAL_RESULTS.md), and [Chapter 6: Discussion and Limitations](docs/CHAPTER_6_DISCUSSION_LIMITATIONS.md). Eleven frozen artifacts were evaluated once for this run. The chronological test partition had already been exposed in earlier reports, so it cannot be described as previously untouched. No frozen operating point reached 85% test recall.
