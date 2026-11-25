# Chapter 3: Methodology and proposed system architecture

## 3.1 Research design and data

The study is an experimental comparison of imbalanced credit-card fraud classifiers using the public ULB/Kaggle dataset. The raw file contains 284,807 transactions, including 492 frauds, with elapsed `Time`, `Amount`, anonymized `V1`–`V28`, and `Class`. Exact duplicate rows are removed before chronological partitioning. The 70/15/15 split uses timestamp boundaries so equal timestamps are not shared across its partitions. The data spans roughly two days, has anonymized components, and does not identify card-present status; it cannot establish CNP-specific or long-term real-world performance. Dataset provenance and the raw-file hash are recorded in the [EDA report](../reports/eda/creditcard_provenance.json).

## 3.2 Preprocessing and features

RobustScaler is fitted to Time and Amount on the relevant training portion only. F0 contains these two scaled values and 28 PCA components. F1 adds sine and cosine of 24-hour elapsed-time phase, log1p amount, rolling amount mean and population standard deviation, and the V14×V17 and V12×V10 interactions. Rolling statistics use up to 1,000 previous rows, zero when no history exists, and stable input order for equal timestamps. Previous chronological history is carried across split boundaries. The phase is relative to the dataset start and is not a verified local hour. The separate F0/F1 contract is described in [metadata](../data/engineered_features/metadata.json).

## 3.3 Models and validation

Balanced L2 Logistic Regression and a balanced Random Forest with 200 trees and depth 12 are compared on F0 and F1 with five expanding TimeSeriesSplit folds on the training partition. Scalers and any learned model preprocessing are fitted within each training fold. Average precision (AP, the project's reported PR-AUC) and ROC-AUC are reported by fold and on the chronological 15% validation partition; AP is not trapezoidal PR area. Equal timestamps may straddle row-index cross-validation folds, so their ordering is a tie-policy limitation. Validation curves describe discrimination rather than a calibrated probability or an operational threshold.

An XGBoost F1 baseline fixes `scale_pos_weight=578` and 200 trees. A seeded genetic algorithm searches learning rate, maximum depth and subsampling using AP on a time-ordered inner validation subset of training. The search uses a fixed population and generation budget with elitism, tournament selection, crossover and mutation. The best candidate is refitted on all training data and compared with the baseline on the later 15% validation set. This small search is not evidence of global optimality. The test split is not used by this experiment; however, it was exposed in previous project work and cannot serve as an untouched confirmatory test.

## 3.4 Proposed architecture and evaluation

The research path is raw transaction data → chronological preparation → versioned feature transformations → training and validation → model and preprocessing artifacts. The prototype serving path uses FastAPI for prediction and explanation, replay through WebSocket/SSE, and a React dashboard; a separate authentication service uses MySQL. TreeSHAP provides model-behaviour attributions rather than causal explanations. A separate feature endpoint accepts explicit rolling history for the new contract. Existing deployed prototype models use an earlier feature contract; these experiments do not automatically replace them. See [Chapter 4](CHAPTER_4_SYSTEM_ARCHITECTURE.md) for implementation details.

Operational evaluation should report AP, ROC-AUC, recall, precision, false alarms, and thresholds chosen before final evaluation. Calibration must be assessed on separate natural-prevalence data before treating scores as probabilities. Latency measurements must identify workload, concurrency, hardware, failure rates and measurement boundaries. A P95 below 100 ms is a project objective, not a verified banking standard or demonstrated production result. Offline-to-serving parity and an independent later dataset remain necessary before deployment claims.
