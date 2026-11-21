# Chapter 1: Introduction

## 1.1 Background

Electronic payment systems process large volumes of transactions and must distinguish legitimate activity from fraudulent activity with limited delay. Fraud detection is difficult because fraudulent transactions are rare, fraud patterns change over time, and a false positive can create operational cost for both customers and investigators. These characteristics make the problem a suitable application for supervised machine learning combined with chronological evaluation and operational decision thresholds.

This project develops a research prototype for credit-card transaction fraud detection using the Kaggle/ULB credit-card dataset. The system combines leakage-safe preprocessing, engineered temporal and amount features, imbalanced-learning strategies, model comparison, TreeSHAP explanations, a FastAPI inference service, chronological replay, and a React monitoring dashboard.

The dataset contains elapsed transaction time, transaction amount, 28 anonymized PCA components (`V1`–`V28`), and a binary fraud label. The PCA components do not retain their original semantic meanings. In addition, the dataset does not identify whether a transaction was card-present or card-not-present. Card-not-present fraud motivates the operational problem addressed by this study, but the experimental results must therefore be described as credit-card transaction fraud results rather than CNP-specific performance.

## 1.2 Problem statement

Fraud detection models may appear effective when evaluated with random splits or accuracy-oriented metrics, even though those procedures can conceal temporal leakage and poor performance on the rare fraud class. A defensible system must use chronological separation, fit learned preprocessing only on earlier data, select thresholds on validation data, and report metrics that remain informative under severe class imbalance. It must also provide explanations and a reproducible path from a scored transaction to a monitoring interface.

The problem addressed in this research is how to design and evaluate a chronological credit-card fraud detection pipeline that combines predictive modelling, imbalance handling, explainability, and a deployable scoring prototype without overstating what the available anonymized dataset can prove.

## 1.3 Aim and objectives

The aim is to implement and evaluate a reproducible machine-learning pipeline for rare credit-card fraud detection with an operational inference demonstration.

The objectives are to:

1. audit and prepare the ULB dataset while preserving chronological order;
2. remove duplicate rows and create chronologically separated training, validation, and evaluation partitions;
3. compare baseline and engineered feature sets using Logistic Regression, Random Forest, and XGBoost;
4. investigate class weighting and training-only oversampling strategies;
5. select alert thresholds using validation data and report PR-AUC, ROC-AUC, precision, recall, F1, and false alarms;
6. provide global and local TreeSHAP explanations;
7. expose prediction and explanation services through FastAPI;
8. demonstrate chronological transaction replay through WebSocket/SSE delivery and a React dashboard; and
9. document the limitations of the dataset, previously exposed evaluation partition, and prototype deployment boundary.

## 1.4 Research questions

- How do engineered temporal, amount, and PCA-interaction features affect fraud-ranking and threshold-based performance relative to the baseline feature set?
- How do class weighting and training-only resampling compare under chronological validation and rare-event metrics?
- How does a validation-selected operating threshold affect recall and false alarms on a later chronological period?
- Can TreeSHAP provide useful local and global evidence for investigating model decisions while preserving the distinction between explanation and causation?
- Can the resulting model artifacts be integrated into a reproducible inference and monitoring prototype?

## 1.5 Scope

The study covers binary classification of the ULB credit-card transactions, chronological preprocessing, model comparison, threshold calibration, SHAP explanation, and local API/dashboard demonstration. The main served models are class-weighted Random Forest and XGBoost artifacts, with Logistic Regression used as a baseline in the research comparison.

The study does not claim deployment in a bank, live access to payment-rail events, causal explanations, guaranteed fraud prevention, or CNP-specific performance. The dashboard demonstrates real-time-like behavior by replaying historical transactions in chronological order. The existing final test partition was previously used in reports and replay code; it must not be described as an untouched test set.

## 1.6 Contributions

The project contributes an auditable implementation that connects research controls to an operational prototype. It records chronological split and leakage safeguards, keeps thresholds separate from final evaluation, provides model-output explanations, and demonstrates how prediction events can be streamed and recorded without storing raw PCA payloads by default. It also makes explicit the distinction between offline model performance, replay behavior, and production monitoring claims.

## 1.7 Thesis structure

Chapter 2 reviews relevant fraud-detection, imbalance, evaluation, chronological-validation, and explainability literature. Chapter 3 describes the data and methodology. Chapter 4 presents the implemented architecture and web prototype. Chapter 5 reports the empirical results. Chapter 6 discusses interpretation, limitations, and future work.
