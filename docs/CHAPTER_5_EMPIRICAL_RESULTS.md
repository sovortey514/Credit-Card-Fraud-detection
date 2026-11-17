# Chapter 5: Empirical Results

## 5.1 Evaluation scope

This chapter reports the Week 18 offline evaluation of saved credit-card fraud classifiers on the final chronological partition of the Kaggle ULB dataset. Evaluation was completed on 15 November 2026. Models were loaded without refitting, and the F1-feature models used thresholds already selected on validation data. No threshold was changed after viewing these results. The experiment measures classification on stored chronological features, rather than end-to-end service performance.

The planned requirement to evaluate a previously untouched test set could not be fulfilled with the existing partition. Earlier imbalance reports already contained test metrics for Logistic Regression, and the threshold-calibration report contained test confusion metrics for the F1 models. The replay implementation also reads this partition, although its complete execution history is unavailable. These results are therefore a frozen-artifact evaluation on a previously exposed chronological test partition. Chronological separation and validation-only threshold selection remain documented safeguards, but do not establish that development decisions were unaffected by earlier test observations.

The [final tables](../reports/final/FINAL_TABLES.md), [machine-readable metrics](../reports/final/metrics.json), [frozen manifest](../reports/final/frozen_manifest.json), and [completion receipt](../reports/final/receipt.json) provide the numerical record. Chapter 6 examines the limits of the evidence.

## 5.2 Dataset and chronological partitions

The raw dataset contains 284,807 transactions, including 492 labelled fraud cases. Removing 1,081 duplicate rows leaves 283,726 transactions and 473 fraud cases. Stable ordering by elapsed `Time` and time-quantile boundaries produce approximately 70%, 15%, and 15% partitions. Tied timestamps account for small departures from exact proportions.

**Table 5.1. Chronological partition composition**

| Partition | Transactions | Fraud | Legitimate | Fraud prevalence | Time range, seconds |
|---|---:|---:|---:|---:|---|
| Training | 198,609 | 366 | 198,243 | 0.184282% | 0–132,906 |
| Validation | 42,560 | 55 | 42,505 | 0.129229% | 132,907–151,320 |
| Test | 42,557 | 52 | 42,505 | 0.122189% | 151,321–172,792 |

Source: [split metadata](../data/processed/creditcard_split_metadata.json). The [leakage audit](../data/processed/creditcard_leakage_audit.json) records strictly separated time ranges and train-only fitting of the amount and time scalers. Week 18 checked the test feature file against the recorded row count, fraud count, ordering, and time endpoints. These checks establish consistency with the saved split record, rather than reconstructing every historical training run.

The test partition spans approximately 5.96 hours within a dataset covering about two days. Its 52 fraud cases provide a small positive-class sample. The reference average precision of an uninformative ranking is near the test prevalence, 0.001222, emphasizing the class imbalance.

## 5.3 Frozen models and decision rules

F0 contains 30 inputs: scaled time, scaled amount, and anonymized PCA components V1–V28. The enhanced F1 feature set adds seven temporal/amount features and six PCA interactions, giving 43 inputs. “F1 features” denotes this feature set; “F1 score” denotes the classification metric.

The inventory was determined from the existing calibration report and two saved F0 baseline artifacts before prediction. Nine F1 artifacts and two F0 artifacts were included. Logistic Regression F1 and Random Forest F1 each appear both as baseline-comparison artifacts and explicitly named class-weight artifacts. Their final metrics coincide; these entries must not be counted as independent replications. The complete final table retains all eleven artifact names, while Table 5.2 presents the seven distinct F1 model/strategy entries.

The saved F1 thresholds came from a validation sweep over 0.01–0.99, minimizing false-positive rate among thresholds attaining at least 85% validation recall, with preference for the higher threshold in a tie. Week 18 loaded these thresholds directly. F0 artifacts had no corresponding saved calibration in this report and used the fixed default of 0.50. Their threshold-dependent results are therefore not a controlled F0-versus-F1 threshold comparison. Class predictions used the inclusive rule `score >= threshold`.

No retraining, resampling, feature modification, threshold search, or deployment-model selection occurred during final evaluation. TreeSHAP bundles and unrelated legacy files were excluded because they are not additional classifiers in the frozen comparison inventory.

## 5.4 Metric definitions

PR-AUC is reported as scikit-learn **average precision (AP)**: the recall-increment-weighted precision summary, rather than trapezoidal integration of the PR curve. ROC-AUC summarizes ranking discrimination over positive–negative pairs. Both use continuous scores and are independent of the reported decision threshold.

F1 score equals `2TP / (2TP + FP + FN)`, and recall equals `TP / (TP + FN)`. Following the earlier calibration report, headline false alarms equal `1,000 × FP / (TN + FP)`: false positives per 1,000 legitimate transactions. The CSV and JSON also provide `1,000 × FP / N`, the measure per 1,000 total transactions. Confusion counts permit independent reconstruction of the operating-point metrics.

## 5.5 Final classification results

**Table 5.2. Enhanced F1 models at saved validation-selected thresholds**

| Model and imbalance strategy | Threshold | PR-AUC (AP) | ROC-AUC | F1 score | Recall | False alarms / 1k legitimate |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression, class weighting | 0.99 | 0.712960 | 0.980799 | 0.597015 | 0.769231 | 0.988119 |
| Logistic Regression, SMOTE | 0.87 | 0.762939 | 0.978075 | 0.661017 | 0.750000 | 0.635219 |
| Logistic Regression, Borderline-SMOTE | 0.91 | 0.726901 | 0.944634 | 0.715596 | 0.750000 | 0.423480 |
| Random Forest, class weighting | 0.21 | 0.778427 | 0.948558 | 0.569444 | 0.788462 | 1.199859 |
| Random Forest, SMOTE | 0.21 | 0.781033 | 0.958730 | 0.512500 | 0.788462 | 1.576285 |
| XGBoost, class weighting | 0.02 | 0.759446 | 0.978857 | 0.472727 | 0.750000 | 1.740972 |
| XGBoost, SMOTE | 0.05 | 0.759943 | 0.972675 | 0.283737 | 0.788462 | 4.611222 |

**Table 5.3. F0 baselines at fixed threshold 0.50**

| Model | PR-AUC (AP) | ROC-AUC | F1 score | Recall | False alarms / 1k legitimate |
|---|---:|---:|---:|---:|---:|
| Logistic Regression, class weighting | 0.710117 | 0.977335 | 0.105389 | 0.846154 | 17.386190 |
| Random Forest, class weighting | 0.780847 | 0.970141 | 0.800000 | 0.730769 | 0.117633 |

**Table 5.4. Confusion counts at the same operating points**

| Model / feature set / strategy | TP | FP | FN | TN | Total alerts |
|---|---:|---:|---:|---:|---:|
| Logistic Regression / F1 / class weighting | 40 | 42 | 12 | 42,463 | 82 |
| Logistic Regression / F1 / SMOTE | 39 | 27 | 13 | 42,478 | 66 |
| Logistic Regression / F1 / Borderline-SMOTE | 39 | 18 | 13 | 42,487 | 57 |
| Random Forest / F1 / class weighting | 41 | 51 | 11 | 42,454 | 92 |
| Random Forest / F1 / SMOTE | 41 | 67 | 11 | 42,438 | 108 |
| XGBoost / F1 / class weighting | 39 | 74 | 13 | 42,431 | 113 |
| XGBoost / F1 / SMOTE | 41 | 196 | 11 | 42,309 | 237 |
| Logistic Regression / F0 / class weighting | 44 | 739 | 8 | 41,766 | 783 |
| Random Forest / F0 / class weighting | 38 | 5 | 14 | 42,500 | 43 |

Random Forest SMOTE has the largest AP among the listed artifacts, 0.781033, closely followed by Random Forest F0 at 0.780847. Their absolute difference is approximately 0.000186 and does not establish statistical superiority. Class-weighted Logistic Regression F1 has the highest ROC-AUC, 0.980799, but lower AP than these Random Forest variants. Model ranking therefore depends on the metric.

Random Forest F0 has the largest observed F1 score, 0.800000, and lowest false-alarm rate. It detects 38 of 52 fraud cases with five false alarms. Its precision is approximately 88.37%, while its recall is 73.08%. Among enhanced F1 models, Borderline-SMOTE Logistic Regression has the highest F1 score, 0.715596: it detects 39 fraud cases with 18 false alarms. These are descriptive comparisons, rather than a decision to replace the served models.

## 5.6 Recall target and feature comparison

**No evaluated artifact attains 85% test recall at its frozen threshold.** Reaching that target with 52 fraud cases requires at least 45 true positives. The greatest observed recall is 44/52, or 84.62%, for Logistic Regression F0, accompanied by 739 false alarms. Enhanced F1 models detect 39–41 fraud cases, giving 75.00–78.85% recall.

The served class-weighted Random Forest's validation recall was 48/55, or 87.27%, but test recall is 41/52, or 78.85%. Class-weighted XGBoost changes from 48/55 to 39/52, or 75.00%. Threshold selection on validation did not guarantee the target in the later period. The test outcomes were retained without threshold adjustment.

In the earlier baseline feature comparison, Logistic Regression validation AP was 0.836650 for F0 and 0.846849 for F1; final AP is 0.710117 and 0.712960 respectively. Random Forest validation AP was 0.860446 for F0 and 0.850297 for F1; final AP is 0.780847 and 0.778427. These observations show no consistent ranking benefit from feature expansion. Because F0 and F1 thresholds differ, differences in recall, false alarms, and F1 score cannot be attributed solely to engineered features.

## 5.7 Supporting explanation and operational evidence

The existing [TreeSHAP benchmark](../reports/explainability/creditcard_treeshap_latency_f1.json) provides supporting validation evidence, separate from the final test evaluation. It records 1,000 analysis rows and 100 latency-benchmark rows, with 50 background medoids selected from training data.

**Table 5.5. Earlier TreeSHAP benchmark**

| Model | Raw mean, ms | Raw P95, ms | k=50 mean, ms | k=50 P95, ms | Global top-3 overlap |
|---|---:|---:|---:|---:|---:|
| Random Forest | 36.192 | 40.884 | 90.657 | 134.199 | 2/3 |
| XGBoost | 26.176 | 43.196 | 26.010 | 32.156 | 2/3 |

The medoid method was slower for Random Forest in this run. XGBoost had a lower recorded P95, but a single small benchmark does not establish a general speedup. Global top-three overlap does not establish per-transaction agreement or complete attribution fidelity. PCA contributions describe model behavior in anonymized feature space, rather than causal reasons for fraud.

The [Week 17 load-test record](WEEK17_LOAD_TEST.md) states that end-to-end latency and maximum throughput have not yet been measured. No claim of production latency compliance or sustained handling of 250 transactions per second is made here.

## 5.8 Reproducibility record

The [evaluator](../scripts/evaluate_frozen_creditcard.py) writes the model inventory, thresholds, feature lists, package versions, and input SHA-256 hashes before prediction. Input hashes are checked again before results are saved. The [receipt](../reports/final/receipt.json) records one prediction pass per artifact and hashes the outputs. Probabilities are retained locally as `reports/final/predictions.npz`, permitting later verification without rescoring.

The evaluator refuses to run when its final directory already exists, including after interruption. This prevents accidental local repeat evaluation but cannot establish that the partition was untouched before Week 18. The evidence supports an offline comparison under recorded conditions, including the failure to transfer the validation recall target and the limitations discussed next.
