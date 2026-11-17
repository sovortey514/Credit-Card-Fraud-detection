# Final chronological test results

Previously exposed test partition; see the frozen manifest. Models and thresholds were fixed before this run.

42,557 transactions, 52 fraud cases. PR-AUC is average precision. False alarms / 1k uses legitimate transactions as its denominator.

## F1 models: saved validation thresholds

| Model | Threshold | PR-AUC (AP) | ROC-AUC | F1 | Recall | False alarms / 1k legitimate | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| logistic_regression_borderline_smote_f1 | 0.91 | 0.726901 | 0.944634 | 0.715596 | 0.750000 | 0.423480 | 39 | 18 | 13 | 42487 |
| logistic_regression_class_weight_f1 | 0.99 | 0.712960 | 0.980799 | 0.597015 | 0.769231 | 0.988119 | 40 | 42 | 12 | 42463 |
| logistic_regression_f1 | 0.99 | 0.712960 | 0.980799 | 0.597015 | 0.769231 | 0.988119 | 40 | 42 | 12 | 42463 |
| logistic_regression_smote_f1 | 0.87 | 0.762939 | 0.978075 | 0.661017 | 0.750000 | 0.635219 | 39 | 27 | 13 | 42478 |
| random_forest_class_weight_f1 | 0.21 | 0.778427 | 0.948558 | 0.569444 | 0.788462 | 1.199859 | 41 | 51 | 11 | 42454 |
| random_forest_f1 | 0.21 | 0.778427 | 0.948558 | 0.569444 | 0.788462 | 1.199859 | 41 | 51 | 11 | 42454 |
| random_forest_smote_f1 | 0.21 | 0.781033 | 0.958730 | 0.512500 | 0.788462 | 1.576285 | 41 | 67 | 11 | 42438 |
| xgboost_class_weight_f1 | 0.02 | 0.759446 | 0.978857 | 0.472727 | 0.750000 | 1.740972 | 39 | 74 | 13 | 42431 |
| xgboost_smote_f1 | 0.05 | 0.759943 | 0.972675 | 0.283737 | 0.788462 | 4.611222 | 41 | 196 | 11 | 42309 |

## F0 baselines: fixed default threshold 0.50

| Model | Threshold | PR-AUC (AP) | ROC-AUC | F1 | Recall | False alarms / 1k legitimate | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| logistic_regression_f0 | 0.50 | 0.710117 | 0.977335 | 0.105389 | 0.846154 | 17.386190 | 44 | 739 | 8 | 41766 |
| random_forest_f0 | 0.50 | 0.780847 | 0.970141 | 0.800000 | 0.730769 | 0.117633 | 38 | 5 | 14 | 42500 |

F0 and F1 are feature-set names; F1 in the metric column is the classification F1 score. Repeated model variants are reported as saved artifacts and are not independent experimental replications.
