# Chapter 2: Literature Review

## 2.1 Credit-card fraud detection

Credit-card fraud detection is a rare-event classification problem in which the positive class is small relative to legitimate activity. Dal Pozzolo et al. describe practical fraud-detection settings as non-stationary: transaction distributions and adversarial behaviour change over time, while labels may arrive after a delay [1]. This motivates chronological validation and careful separation between model development and later evaluation. A model that performs well on a random split may benefit from information patterns that would not be available when a future transaction is scored.

The ULB/Kaggle dataset used here is valuable for reproducible benchmarking because it contains a public binary label and anonymized transaction variables. However, the PCA transformation removes direct semantic interpretation of `V1`–`V28`, and no payment-channel field identifies card-present or card-not-present transactions. Results from this dataset therefore support general credit-card transaction-fraud analysis, not a claim about CNP-only fraud.

## 2.2 Temporal validation and leakage control

Random cross-validation assumes that observations are exchangeable. That assumption is questionable when transaction order, delayed labels, customer behaviour, or attacker adaptation matter. Chronological splitting better reflects deployment: training examples precede validation examples, which precede the final evaluation period. Learned scalers and distribution statistics must be fitted on training data only. Resampling must also be applied only to training folds, because transforming or oversampling validation/test data changes the evaluation distribution.

This project sorts transactions by `Time`, removes duplicate rows, uses chronological partitions, fits RobustScaler objects on training data, and carries rolling amount history forward only in time order. The inference prototype uses explicitly scoped rolling-history contexts for replay so that one stream does not contaminate another.

## 2.3 Metrics for extreme imbalance

Accuracy is weak evidence when legitimate transactions dominate. A classifier can obtain high accuracy while missing many fraud cases. ROC-AUC measures ranking across thresholds and remains useful for comparing discrimination, but it can appear optimistic when the negative class is very large. Precision-recall analysis focuses on the trade-off between detecting positives and generating false alerts. Average precision (AP), reported here as PR-AUC in the project tables, is therefore particularly informative for rare fraud.

Threshold-dependent measures remain essential for operations. Recall measures the proportion of fraud cases detected, while precision measures the proportion of alerts that are fraud. F1 summarizes precision and recall but does not encode the asymmetric operational cost of missed fraud and investigator workload. This study additionally reports false alarms per 1,000 legitimate transactions and selects thresholds on validation data rather than tuning against the final evaluation partition.

## 2.4 Class weighting and resampling

Class weighting changes the loss contribution of the minority class without synthesizing new examples. It is often attractive for tree and linear models because it preserves the observed feature distribution and is computationally simple. SMOTE generates synthetic minority examples by interpolating between minority neighbours [2]. It can improve minority representation, but synthetic examples may be less realistic when the minority class is heterogeneous or temporally structured. Borderline-SMOTE concentrates synthesis near difficult decision boundaries, which can help some classifiers but may also amplify ambiguous points.

The comparison must be performed fairly: weighting or resampling is fitted within the training data only, while validation and final evaluation remain at their natural prevalence. The project therefore treats class weighting, SMOTE, and Borderline-SMOTE as alternative training strategies, not as transformations applied to held-out transactions. Their value is judged with AP, ROC-AUC, threshold metrics, false alarms, and computational evidence rather than accuracy alone.

## 2.5 TreeSHAP explainability

Lundberg et al. introduce TreeSHAP as an efficient method for computing Shapley-value explanations for tree ensembles [3]. A SHAP value describes the contribution of a feature to a model output relative to a baseline under the explainer's assumptions. This supports global rankings and local investigation of true-positive and false-positive cases. In this project, TreeSHAP is used for Random Forest and XGBoost artifacts and the dashboard displays signed local contributions.

SHAP explanations are explanations of model behaviour, not causal effects. The anonymized PCA components cannot be given domain meanings that the dataset does not provide. Correlated features can also distribute attribution in ways that depend on the explainer's conditional assumptions. Consequently, SHAP should support analyst investigation and model debugging, not be presented as proof that a transaction feature caused fraud.

## 2.6 Real-time scoring and monitoring

A useful fraud system must connect a trained artifact to a low-latency scoring path, a decision threshold, an explanation mechanism, and an audit/monitoring layer. Historical replay is a reproducible way to test ordering, latency, acknowledgement, and alert rendering when a live payment stream is unavailable. It is not equivalent to production deployment. Persistent monitoring should distinguish request volume, latency, alert rate, model version, and delayed outcome-based performance. Prediction history must retain enough provenance to identify the model, feature contract, threshold, and source of an event while respecting data minimization.

The present prototype implements FastAPI prediction/explanation routes, chronological WebSocket/SSE replay, scoped rolling state, SHAP inspection, and non-sensitive prediction-history summaries. Authentication is provided by a separate service. Production access control, external state for horizontally scaled rolling contexts, drift response, and live payment integration remain future work.

## 2.7 Summary and research gap

Prior work establishes the importance of non-stationarity, imbalance-aware evaluation, temporal safeguards, and explainable tree models. The implementation developed here combines those concerns in one reproducible workflow and reports their limitations explicitly. The main research gap addressed is practical integration: a chronology-aware training/evaluation pipeline is connected to versioned model artifacts, state-aware replay inference, explanations, and dashboard-level operational evidence without claiming that a public anonymized dataset represents all real-world CNP fraud.

## References

See `docs/BIBLIOGRAPHY.md` for complete citation details.
