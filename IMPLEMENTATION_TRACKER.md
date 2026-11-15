# Fraud Detection Project Implementation Tracker

Last reviewed: 2026-11-15

## Initial project setup

| Task | Status | Evidence / notes |
|---|---|---|
| Initialize Git repository | Complete | Git repository metadata exists in the project root. |
| Create `data/raw` | Complete | Directory exists. |
| Create `src/features` | To do | Directory was not found during the review. The current feature code is under `src/fraud_detection/`. |
| Create `src/models` | To do | Directory was not found during the review. |
| Create `api` | To do | Directory was not found during the review. The current API code is in the project root and `backend/`. |
| Create `tests` | Complete | Directory exists. |

## Dependencies

| Task | Status | Evidence / notes |
|---|---|---|
| Configure Python 3.11 | Partial | Python 3.11 is not explicitly pinned in the dependency configuration. |
| Add XGBoost | Complete | `xgboost` is listed in `requirements.txt`. |
| Add scikit-learn | Complete | `scikit-learn` is listed in `requirements.txt`. |
| Add imbalanced-learn | Complete | `imbalanced-learn` is listed in `requirements.txt`. |
| Add FastAPI | Complete | `fastapi` is listed in `requirements.txt`. |
| Add SHAP | Complete | `shap` is listed in `requirements.txt` and used by `src/explainability.py`. |

## Reproducible local execution

| Task | Status | Evidence / notes |
|---|---|---|
| Create Dockerfile | Partial | `Dockerfile` exists, but it uses Python 3.12 instead of the requested Python 3.11. |
| Create docker-compose.yml | Complete | `docker-compose.yml` exists and defines the local API and MySQL services. |

## Reproducibility

| Task | Status | Evidence / notes |
|---|---|---|
| Define `SEED = 42` | Complete | Defined in `src/fraud_detection/config.py`. |
| Seed Python and NumPy | Complete | `seed_everything()` seeds both Python's `random` module and NumPy. |

## Next actions

- Create `src/features/`, `src/models/`, and `api/` if these paths are required by the final project structure.
- Decide whether the project standard is Python 3.11 or 3.12, then align the Dockerfile and documentation.
- Add an explicit Python version configuration if Python 3.11 is required.

## Research and thesis writing

| Task | Status | Evidence / notes |
|---|---|---|
| Review Dal Pozzolo et al. on credit-card fraud | To do | No paper notes, citation, or bibliography entry was found. |
| Review Lundberg et al. TreeSHAP | Partial | SHAP `TreeExplainer` is implemented in `src/explainability.py`, but the paper review and citation are missing. |
| Synthesize PR-AUC vs ROC-AUC literature | Partial | The code calculates both metrics in the model training scripts, but no written literature synthesis was found. |
| Synthesize SMOTE vs class-weighting literature | Partial | SMOTE/SMOTE-Tomek and class weighting are implemented, but no written comparison of the literature was found. |
| Draft Chapter 1: Introduction | To do | No Chapter 1 draft was found. |
| Draft Chapter 2: Literature Review | To do | No Chapter 2 draft or bibliography was found. |
| Focus the chapters on card-not-present fraud and PCA features | To do | Credit-card PCA features `V1`–`V28` are implemented in the feature pipeline, but this focus has not been documented in thesis chapters. |

## Credit-card dataset and EDA

Audit performed against `data/raw/creditcard.csv` on 2026-11-15.

| Task | Status | Verified result / evidence |
|---|---|---|
| Download Kaggle `creditcard.csv` into `data/raw/` | Complete | File exists at `data/raw/creditcard.csv`; size is 150,828,752 bytes. |
| Verify transaction count | Complete | 284,807 transactions. |
| Verify fraud count and rate | Complete | 492 fraud cases; fraud rate is 0.1727%. |
| Record SHA-256 hash | Partial | Current hash: `76274B691B16A6C49D3F159C883398E03CCD6D1EE12D9D8EE38F4B4B98551A89`. It should be saved in a dedicated credit-card provenance report. |
| Inspect `Time` span | Complete | `Time` ranges from 0 to 172,792 seconds, or approximately 48 hours. |
| Inspect `Amount` skewness | Complete | Amount skewness is 16.977724, confirming strong right skew. |
| Inspect `V1`–`V28` distributions | Complete | Saved in `reports/eda/creditcard_pca_distributions.png`; the full-dataset summary is recorded in `reports/eda/creditcard_eda_summary.json`. |
| Check missing values | Complete | 0 missing cells. |
| Check duplicate rows | Complete | 1,081 duplicate rows were found. The dataset therefore does not satisfy a zero-duplicate expectation until duplicates are handled. |

## Chronological preprocessing and leakage control

Audit performed against the generated files in `data/processed/` on 2026-11-15.

| Task | Status | Verified result / evidence |
|---|---|---|
| Sort `creditcard.csv` by `Time` | Complete | `prepare_creditcard.py` uses stable ascending `Time` order before deduplication and splitting. |
| Create 70/15/15 chronological partitions | Complete | After removing 1,081 duplicate rows: train 198,609 rows, validation 42,560 rows, test 42,557 rows. Time ranges do not overlap. |
| Fit `RobustScaler` on train only | Complete | `Amount` and `Time` scalers are fitted on the train partition; validation and test are transformed only. |
| Perform leakage audit | Complete | `creditcard_leakage_audit.json` reports all split-order and no-future-to-past checks as `true`. |
| Save processed Parquet files | Complete | `creditcard_train.parquet`, `creditcard_validation.parquet`, and `creditcard_test.parquet` exist in `data/processed/`. |

## Credit-card feature engineering

Audit performed against the generated feature files and metadata on 2026-11-15.

| Task | Status | Verified result / evidence |
|---|---|---|
| Build baseline F0 features | Complete | F0 contains `scaled_time`, `scaled_amount`, and `V1`–`V28`; train, validation, and test feature Parquet files exist. |
| Build engineered F1 features | Complete | F1 contains cyclical `hour_sin`/`hour_cos` and `amount_log1p`. |
| Compute chronological amount statistics | Complete | Global z-score/percentile and rolling z-score/percentile features are generated. Global statistics are fit from train; rolling calculations use prior rows in chronological order. |
| Create PCA interaction features | Complete | Six pairwise interactions are generated among `V14`, `V17`, `V12`, and `V10`. |
| Validate feature implementation | Complete | `tests/test_creditcard_features.py`: 2 tests passed. |

## Production preprocessing and inference validation

Audit performed on 2026-11-15.

| Task | Status | Evidence / notes |
|---|---|---|
| Wrap F0/F1 in a scikit-learn `Pipeline` / `ColumnTransformer` | Complete | `preprocessing_pipeline.py` provides a train-fitted scikit-learn `Pipeline` that emits legacy API columns plus F0/F1 and interaction features. |
| Test batch features against single-row API inference | Complete | `test_batch_and_single_row_pipeline_outputs_match` verifies matching output for the same transaction. |
| Benchmark transformation latency below 2 ms per transaction | Complete | 1,000-transaction benchmark: 0.189739 ms per transaction. |
| Serialize fitted preprocessing pipeline with joblib | Complete | `models/creditcard_preprocessing.joblib` is generated and reloads as a scikit-learn `Pipeline`. |
| Validate preprocessing implementation | Complete | `tests/test_creditcard_features.py`: 4 tests passed. |

## Baseline model comparison and validation curves

Completed on 2026-11-15 with `scripts/compare_creditcard_models.py`.

| Task | Status | Verified result / evidence |
|---|---|---|
| Train Logistic Regression baseline | Complete | L2 Logistic Regression with `class_weight="balanced"`, fitted for F0 and F1. |
| Train Random Forest baseline | Complete | Random Forest with `n_estimators=200`, `max_depth=12`, and `class_weight="balanced"`, fitted for F0 and F1. |
| Compare F0 vs F1 with 5-fold `TimeSeriesSplit` | Complete | Five chronological folds were run for both models and both feature sets on the training partition. |
| Plot validation Precision-Recall curve | Complete | Saved to `reports/models/creditcard_validation_precision_recall.png`. |
| Plot validation ROC curve | Complete | Saved to `reports/models/creditcard_validation_roc.png`. |
| Save comparison metrics and model bundles | Complete | Metrics saved to `reports/models/creditcard_f0_f1_comparison.json`; four model bundles saved under `models/creditcard/`. |

Validation highlights:

- Best validation average precision: Random Forest F0, `0.8604`.
- Best validation ROC-AUC: Logistic Regression F1, `0.9849`.

## Class imbalance handling

| Task | Status | Evidence / notes |
|---|---|---|
| Cost-sensitive weighting | Implemented | `scripts/compare_imbalance_strategies.py` uses `class_weight="balanced"` for Logistic Regression and Random Forest, and computes XGBoost `scale_pos_weight` from the chronological training partition. |
| SMOTE on training data only | Implemented | The same script applies `SMOTE(sampling_strategy=0.1, random_state=42)` only to the 70% training partition; validation and held-out test data remain untouched. |
| Borderline-SMOTE on training data only | Implemented | The same script supports `BorderlineSMOTE(sampling_strategy=0.1, random_state=42)` and never resamples validation or test data. |
| Compare weighting, SMOTE, and Borderline-SMOTE | Complete for Logistic Regression | F1 benchmark saved in `reports/models/creditcard_imbalance_f1.json`; the script also supports Random Forest and XGBoost. |
| Benchmark time, memory, validation PR-AUC, and FPR | Complete for Logistic Regression | The benchmark records resampling time, model-fit time, peak traced memory, validation/test average precision, and FPR at threshold 0.5. |

## Week 10: threshold calibration

| Task | Status | Evidence / notes |
|---|---|---|
| Sweep thresholds from 0.01 to 0.99 | Implemented | `scripts/tune_creditcard_thresholds.py` evaluates the validation probabilities at 99 thresholds. |
| Select threshold for Recall >= 85% with minimal false alarms | Implemented | Threshold is selected from validation data by minimizing validation FPR among thresholds meeting the recall target. |
| Quantify false alarms per 1,000 transactions | Implemented | Reports `false_alarms_per_1000` for validation and held-out test predictions. |
| Compare calibrated threshold with 0.50 | Implemented | JSON and CSV reports contain default 0.50 and calibrated metrics for both validation and test splits. |

## Week 11: TreeSHAP explainability

| Task | Status | Evidence / notes |
|---|---|---|
| Initialize TreeSHAP for final Random Forest and XGBoost | Implemented | `scripts/explain_tree_models.py` loads the final F1 class-weighted tree artifacts and initializes `shap.TreeExplainer`. |
| Compute global SHAP values on validation transactions | Implemented | SHAP values are computed across the full chronological validation partition. |
| Generate beeswarm and mean absolute SHAP plots | Implemented | Per-model plots and ranked CSVs are saved under `reports/explainability/`. |
| Inspect local true-positive and false-positive explanations | Implemented | Representative validation TP and FP waterfall plots are generated at each model's calibrated threshold. |

## Week 12: TreeSHAP optimization and deployment artifacts

| Task | Status | Evidence / notes |
|---|---|---|
| Benchmark raw TreeSHAP inference latency per transaction | Implemented | `scripts/benchmark_treeshap.py` records mean, median, and p95 milliseconds per validation transaction. |
| Compress background data with K-Means medoids, k=50 | Implemented | K-Means is fit on chronological training features and the nearest actual training row for each centroid is saved as the medoid background. |
| Verify top-3 SHAP ranking fidelity | Implemented | The report compares exact raw TreeSHAP and k=50-medoid TreeSHAP rankings using top-3 overlap. |
| Serialize final XGBoost/RF model and TreeSHAP explainers | Implemented | Raw and k=50-medoid bundles are serialized under `models/creditcard/`. |

## Week 13: FastAPI inference service

| Task | Status | Evidence / notes |
|---|---|---|
| Build FastAPI backend under `/app/api`, `/app/schemas`, and `/app/services` | Implemented | Application entry point and versioned routes are in the new `app/` package. |
| Define Pydantic schema for 30 credit-card fields | Implemented | `CreditCardTransaction` validates `Time`, `Amount`, and `V1`-`V28` with extra fields forbidden. |
| Implement `POST /api/v1/predict` and `POST /api/v1/explain` | Implemented | Both endpoints support the calibrated XGBoost and Random Forest models. |
| Add API integration tests | Implemented | `tests/test_api.py` covers prediction, SHAP explanation, and invalid payload validation. |

## Week 14: chronological replay and streaming

| Task | Status | Evidence / notes |
|---|---|---|
| Replay the 15% held-out set in Time order | Implemented | `scripts/replay_creditcard.py` and `CreditCardReplayService` read `creditcard_test.parquet`, sort by `Time`, and score each raw transaction. |
| Configure replay speed at 10, 50, 100, or 250 transactions/second | Implemented | CLI and API validation restrict speed to the four requested values. |
| Push scored events through SSE and WebSocket | Implemented | `GET /api/v1/replay/stream` provides SSE and `WS /api/v1/replay/ws` provides acknowledged event delivery. |
| Verify zero dropped messages during burst replay | Implemented | WebSocket events carry sequence IDs and require matching acknowledgements; integration test confirms 5/5 delivered and `dropped: 0`. |

## Week 15: live React dashboard

| Task | Status | Evidence / notes |
|---|---|---|
| Finalize React + TypeScript Vite + Tailwind dashboard | Implemented | `frontend/src/LiveDashboard.tsx` is the Vite entry view and Tailwind/PostCSS configuration is included. |
| Connect WebSocket client to live transaction feed | Implemented | The dashboard connects to `/api/v1/replay/ws`, sends replay configuration, and acknowledges every event. |
| Display Tx/sec, P95 latency, review queue, and high-risk alerts | Implemented | KPI cards calculate values from live scored events and backend model latency. |
| Add click-to-inspect flagged transaction drawer | Implemented | Flagged rows open a responsive drawer showing score, threshold, latency, amount, model, and V14/V17/V12/V10 inputs. |
| Add login page and role-based user management | Implemented | The live dashboard reuses `AuthScreen` and `UserManagement`; `admin` and `super_admin` roles can manage users, while standard users remain on the monitor view. |

