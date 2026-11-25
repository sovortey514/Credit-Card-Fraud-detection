# Validation error analysis at the default cutoff

The comparison uses the 42,560-row chronological validation partition (42,505 legitimate and 55 fraud), the same F1 features, and the inclusive rule `score >= 0.50`. Logistic Regression and Random Forest are the balanced Task 7 models, XGBoost is the GA-selected Task 8 model with positive-class weight 578, and LightGBM is a new balanced baseline with 200 trees and maximum depth 12. The models differ in training and weighting; a common numerical threshold does not imply a common calibrated risk. Results are development-set observations, not independent final-test or production estimates.

| Model | True negatives | False positives | False negatives | True positives | Precision | Recall | False alarms / 1,000 legitimate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 40,844 | 1,661 | 4 | 51 | 2.98% | 92.73% | 39.08 |
| Random Forest | 42,505 | 0 | 14 | 41 | 100.00% | 74.55% | 0.00 |
| LightGBM | 42,503 | 2 | 13 | 42 | 95.45% | 76.36% | 0.05 |
| XGBoost + GA | 42,502 | 3 | 13 | 42 | 93.33% | 76.36% | 0.07 |

See the [confusion matrices](../reports/validation_errors/confusion_matrices.png) and [machine-readable results](../reports/validation_errors/comparison.json). Zero observed false alarms for Random Forest does not establish zero underlying false-alarm risk. With only 55 fraud cases, each missed fraud changes measured recall by about 1.82 percentage points; estimates and differences are uncertain.

## Failure cases

At 0.50, Logistic Regression detects 51 of 55 frauds but generates 1,661 false alerts; its four missed frauds have a median Amount of 2.59, while its false alerts have a median Amount of 12.31. Random Forest misses 14 frauds (median Amount 6.245) and has no observed false alerts. LightGBM and XGBoost + GA each miss 13 frauds (median Amount 4.49) and produce two and three false alerts, respectively. These are descriptive summaries of small groups, not evidence that low amount causes mistakes; V1–V28 are anonymized and cannot support an explanation of transaction intent. The counts do not establish that different models missed the same individual transactions.

## Operational precision–recall trade-off

At the 0.50 cutoff, Logistic Regression creates 1,712 alerts for 51 detected frauds; reviewing all alerts would require a much larger investigation capacity than the 45 alerts from XGBoost + GA for 42 detected frauds. Conversely, the latter misses nine more frauds in this sample. For XGBoost + GA, lowering the cutoff to 0.10 detects 44 of 55 frauds and increases false alerts from 3 to 10; precision changes from 93.33% to 81.48%. These are observed counts under this validation prevalence, not expected bank-wide volumes or estimated monetary costs.

Threshold choice should reflect confirmed fraud loss, customer friction, investigator capacity, and the relative costs of false positives and false negatives. A bank should estimate those quantities on representative, appropriately labeled data and select its operating point on a separate validation period, then assess it on an independent later period. The additional threshold examples in the results file are descriptive; selecting one after inspecting these outcomes would reuse this validation set. Class weighting affects scores, and no probability calibration has been established. No production threshold recommendation or guarantee follows from this benchmark.
