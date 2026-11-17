# Chapter 6: Discussion and Limitations

## 6.1 Interpretation of the findings

The frozen models distinguish many fraudulent transactions from legitimate transactions in the ULB chronological test partition, but none reaches the specified 85% recall target at its retained operating point. The findings support the feasibility of offline fraud ranking on this dataset while showing that the selected validation operating points do not satisfy the final recall requirement. Strong area-under-curve scores alone are insufficient evidence of acceptable fraud prevention.

As reported in [Chapter 5](CHAPTER_5_EMPIRICAL_RESULTS.md), Random Forest F0 combines an F1 score of 0.800000 with five false alarms, but misses 14 of 52 fraud cases. Logistic Regression F0 detects 44 fraud cases but generates 739 false alarms. These results illustrate the tension between missed fraud and review workload. They do not identify an optimal bank decision rule because fraud losses, investigation costs, customer friction, and review capacity were not incorporated into the objective.

## 6.2 Discrimination and operational decisions

Class-weighted Logistic Regression F1 has the largest observed ROC-AUC, 0.980799, whereas Random Forest SMOTE has the largest AP, 0.781033. ROC-AUC summarizes discrimination against the full legitimate population; AP emphasizes precision as fraud recall changes and is sensitive to prevalence. The two metrics answer related but different questions.

Strong ROC-AUC can coexist with substantial investigation workload. Class-weighted XGBoost has ROC-AUC 0.978857, yet its threshold produces 74 false positives and 39 true positives. AP also cannot specify an acceptable threshold without a policy for recall and review cost. Area-under-curve metrics should therefore be read alongside confusion counts and operating-point performance.

False alarms per 1,000 legitimate transactions are not the proportion of alerts that are false. Class-weighted Random Forest F1 produces approximately 1.20 false alarms per 1,000 legitimate transactions, yet 51 of its 92 alerts are false positives, approximately 55.43%. Explicit denominators and precision help distinguish the population false-positive rate from the usefulness of the alert queue.

## 6.3 Transfer of the validation recall target

Saved thresholds achieved at least 85% validation recall but only 75.00–78.85% test recall for enhanced F1 variants. This is an observed failure to transfer the target to the later period. Its cause is unresolved: sampling variation, changes in the types of fraud, feature-distribution changes, and threshold-selection variability could contribute. The difference alone does not prove concept drift.

The test partition contains only 52 positive cases. Each additional detected or missed fraud changes recall by approximately 1.92 percentage points. Validation threshold selection similarly relied on only 55 fraud cases and a finite grid. No confidence intervals, repeated chronological windows, or paired significance tests were computed for this final comparison. The AP difference of 0.000186 between Random Forest SMOTE and Random Forest F0 does not support a claim of reliable superiority.

Changing thresholds after these observations would use the test partition for tuning. The thresholds were retained and the target failure was reported. Future threshold-policy development requires a new development window followed by independent evaluation. The current evidence does not justify an 85% operational recall guarantee.

## 6.4 Feature engineering and imbalance handling

The enhanced feature set did not consistently improve discrimination over F0. Logistic Regression improved slightly in test AP, whereas the baseline Random Forest F1 artifact had slightly lower AP than F0. This does not establish that any individual engineered feature is helpful or harmful: a controlled ablation study was not performed.

F0 used threshold 0.50 while F1 used validation-selected thresholds. Differences in recall, false alarms, and F1 score therefore combine feature, fitted-model, and threshold-policy effects. A future controlled feature study should apply comparable model-selection and threshold objectives to both feature sets before an independent final evaluation.

SMOTE likewise provides no uniform advantage. Logistic Regression SMOTE increases AP from 0.712960 to 0.762939 and reduces false positives from 42 to 27, but detects one fewer fraud at its saved threshold. Borderline-SMOTE detects the same 39 fraud cases as SMOTE with fewer false positives, despite lower AP and ROC-AUC. Random Forest SMOTE detects the same 41 frauds as class weighting while increasing false positives from 51 to 67. XGBoost SMOTE increases detections from 39 to 41 but increases false positives from 74 to 196.

These results concern particular configurations and operating points, rather than establishing a universally preferable imbalance method. Synthetic observations in transformed feature space do not establish that equivalent transactions occur in practice. Resampling was implemented only on training data, and test prevalence was retained. The saved inventory includes Borderline-SMOTE Logistic Regression but lacks comparable frozen Borderline-SMOTE tree models, limiting cross-family conclusions.

## 6.5 Prior test exposure

The central methodological limitation is prior test exposure. Before Week 18, both the imbalance comparison and threshold-calibration reports contained test outcomes. Threshold selection is explicitly implemented on validation predictions, but this does not prove that earlier test observations had no influence on model families, features, or research decisions. Complete historical decision logs are unavailable.

The Week 18 manifest and receipt establish a single prediction pass per listed artifact for this run, with frozen inputs and cached scores. This improves reproducibility but cannot restore an untouched test set retrospectively. The findings should be presented as evaluation on a previously exposed chronological partition, rather than a pristine confirmatory estimate. No post hoc re-partitioning was performed to disguise the exposure.

A stronger confirmatory claim requires genuinely new later data. Models, preprocessing definitions, thresholds, metrics, and the evaluation protocol should be fixed before label access, with an access log. Reusing the current partition for tuning or deployment-model selection would further weaken its role as final evidence.

## 6.6 Dataset scope and external validity

The dataset covers approximately two days, with a final test window of approximately six hours. It cannot establish stability across weeks, holidays, merchant populations, regions, or evolving fraud strategies. Fraud prevalence differs between partitions, but the reasons were not established.

The records do not identify card-present versus card-not-present payments. These results cannot be described as a CNP-only evaluation. They also do not validate money-transfer fraud detection or real bank operations, despite the repository's project name. The empirical evidence concerns the supplied anonymized credit-card data.

V1–V28 do not reveal their original business meanings. Missing cardholder and merchant identifiers prevent entity-specific behavioral analysis and entity-disjoint evaluation. Global rolling statistics summarize the transaction stream rather than individual card histories. The provided PCA transformation cannot be reconstructed from this repository, so train-only fitting claims apply to the project's own learned preprocessing steps.

Deduplication changes the population: 1,081 duplicate rows, including 19 fraud-labelled rows, are removed. This prevents exact duplicate records from spanning the project partitions, but conclusions apply to the deduplicated population. Delayed labels, label error, recovered fraud losses, and human investigation outcomes were not evaluated.

## 6.7 Offline and service preprocessing

The final evaluation uses stored chronological features produced by the [offline feature engineer](../src/fraud_detection/engineer_creditcard_features.py). Its rolling z-score uses prior amounts, while its rolling percentile uses current-or-prior observations. History carries across chronological partitions without requiring future labels.

The [API transformer](../src/fraud_detection/preprocessing_pipeline.py) uses different history semantics. Its rolling z-score uses fixed statistics from the end of training rather than updating during replay. Its rolling percentile searches the largest sorted training amounts instead of a chronological trailing window. These definitions differ from those in the offline model-comparison features.

Consequently, offline test accuracy cannot be assumed to reproduce the API's predictions or service accuracy. Batch-versus-single-row parity within the API transformer does not establish parity with historical training features. A shared causal history policy and explicit offline-versus-service feature checks are required. Any subsequent preprocessing or model change requires fresh validation and independent evaluation. The frozen artifacts were preserved during Week 18.

## 6.8 Explanation and operational limitations

TreeSHAP helps inspect how inputs contribute to model scores but does not establish why transactions are actually fraudulent. Anonymized PCA features limit direct business interpretation. Correlated interactions can affect attribution allocation, and background selection changes the comparison reference. Explanation values must be interpreted in the explainer's output units rather than assumed to be probability changes.

The earlier benchmark shares two features among the global top three for both tree models. This narrow global comparison does not establish equivalent local explanations, complete ranking fidelity, or analyst usefulness. The latency benchmark used only 100 transactions. Random Forest became slower with the 50-medoid background, so background compression cannot be presented as a general optimization success.

End-to-end load results are unavailable. Isolated explanation timing does not include all network, preprocessing, serialization, queuing, authentication, and dashboard costs. It cannot establish throughput or P95 compliance under concurrency. Replay acknowledgements do not prove zero dropped messages at every intended rate. Service testing and operational controls remain necessary before deployment claims.

Scores have not been shown to be calibrated fraud probabilities. Class weighting and oversampling alter learning objectives and class proportions, so an output of 0.90 is not a verified 90% real-world fraud probability. This final experiment includes no probability-calibration study, cost-based decision analysis, fairness assessment, adversarial robustness evaluation, or prospective monitoring study.

## 6.9 Implications and future work

The evidence favors describing decision profiles rather than declaring a universal winning model. Random Forest F0 has a low observed alert burden but falls below the recall target. The class-weighted trees served by the prototype also miss the target. The tables inform future research but do not establish a production model choice.

The next work should align offline and service preprocessing under a common causal history policy. Development should then specify whether decisions optimize minimum recall, investigation capacity, fraud loss, or a combination. Thresholds and any probability calibration must be fitted within development data, then frozen before independent later evaluation. Longer time windows, more positive cases, repeated temporal validation, and dependence-aware uncertainty estimates would strengthen conclusions about stability.

Operational follow-up should measure prediction and explanation together under representative arrival rates, recording errors, delivery counts, and latency under concurrent demand. Investigator studies can assess whether explanations and alerts assist review. A CNP-specific research question requires an explicit payment-channel field in new data. These extensions address the gaps identified here while retaining the present reproducible numerical record.
