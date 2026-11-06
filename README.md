# Money Transfer Fraud Detection — Full Research Project

**This is the complete project workspace**, not a Week 1-only folder. It contains a working baseline ML pipeline, a FastAPI scoring service, a simple React dashboard, tests, a replay script, and a 20-week roadmap. Some advanced components (historical feature engineering, streaming alerts, load testing) are planned work, not already implemented.

## Requirements
- Windows 11, VS Code, Python 3.11 or 3.12, Node.js 20+
- Download the PaySim CSV from https://www.kaggle.com/datasets/ealaxi/paysim1 and save it as `data/raw/paysim.csv` (not bundled).
- Use a sufficiently large PaySim sample for chronological splits; the full CSV can be large.

## Install (PowerShell from the project root)
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```
If Python 3.11 is unavailable, replace `-3.11` with `-3.12`.

## 1. Dataset exploration
```powershell
.\.venv\Scripts\python.exe -m src.fraud_detection.eda
```
Outputs: `reports/dataset_summary.csv`, `reports/transaction_types.csv`.

## 2. Train and compare three models
```powershell
.\.venv\Scripts\python.exe -m src.fraud_detection.train
```
Outputs: `models/fraud_model.joblib` and `reports/model_results.json`. If any chronological split lacks fraud examples, use a larger dataset. Training on the full PaySim file may take time and RAM.

## 3. Start API (new terminal)
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```
Open http://127.0.0.1:8000/docs . Health endpoint: http://127.0.0.1:8000/health .

## 4. Start React dashboard (another terminal)
```powershell
cd frontend
npm install
npm run dev
```
Open http://127.0.0.1:5173 . Score a test transfer using the form.

## 5. Replay synthetic transactions (optional)
In another terminal at the project root:
```powershell
.\.venv\Scripts\python.exe scripts/replay.py --limit 20 --delay 0.5
```
This prints API results to the terminal; automatic dashboard streaming is **not yet implemented**.

## 6. Run tests
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Structure
- `data/`: PaySim input and derived data (raw CSV excluded from ZIP)
- `src/fraud_detection/`: features, EDA, model comparison
- `models/`: serialized trained model (generated)
- `backend/`: FastAPI service
- `frontend/`: React/TypeScript web UI
- `scripts/`: replay helper
- `tests/`: automated checks
- `reports/`: experimental outputs
- `docs/`: full research roadmap

## Important scientific limitations
The initial pipeline is a **baseline**. It has no historical behavioral aggregates yet. It selects the best model by validation average precision and selects a decision threshold on validation F1. It uses a chronological split and excludes post-transfer balances. Test results must be interpreted only for synthetic PaySim, not for real KHQR/bank operations. The first milestone is to run EDA successfully, then improve feature engineering and validation in later phases.
