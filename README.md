# Credit Card Fraud Detection

Research and application code for imbalanced credit-card fraud detection using the Kaggle ULB dataset. It contains transaction time, amount, anonymized PCA components (`V1`–`V28`), and the `Class` label. The data does not identify card-present versus card-not-present transactions, so results cannot be described as a CNP-only evaluation.

## Requirements

- Windows 11, Python 3.12 (or the Python version supported by the selected environment), and Node.js 20+ for the dashboard.
- Place `creditcard.csv` at `data/raw/creditcard.csv`. The raw dataset is excluded from version control.

## Prepare the data

```powershell
.\.venv\Scripts\python.exe scripts/verify_data.py
.\.venv\Scripts\python.exe -m src.fraud_detection.eda
.\.venv\Scripts\python.exe -m src.fraud_detection.prepare_creditcard
.\.venv\Scripts\python.exe -m src.fraud_detection.engineer_creditcard_features
```

Preparation sorts by time, removes duplicate rows, creates chronological train/validation/test partitions, fits scaling on training data only, and writes Parquet files and audit metadata under `data/processed/`.

## Fit preprocessing and compare models

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
