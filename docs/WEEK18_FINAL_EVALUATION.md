# Week 18: final evaluation and thesis chapters

Completed on 2026-11-15. Eleven saved classifier artifacts were each scored once on the existing final chronological partition: 42,557 rows, 52 fraud cases, and 42,505 legitimate transactions. No models were fitted and no thresholds were searched. Nine F1 artifacts used saved validation thresholds; two F0 baselines used the fixed default of 0.50.

| Requested work | Status | Evidence |
|---|---|---|
| Evaluate frozen models once | Complete for this Week 18 run | [Receipt](../reports/final/receipt.json), [manifest](../reports/final/frozen_manifest.json) |
| Use a previously untouched 15% chronological test set | Not satisfied by existing data | Earlier calibration and imbalance reports already contain test metrics; replay also reads this partition |
| Compile PR-AUC, ROC-AUC, F1, recall, false alarms / 1k | Complete | [Tables](../reports/final/FINAL_TABLES.md), [CSV](../reports/final/metrics.csv), [JSON](../reports/final/metrics.json) |
| Write Chapter 5 | Draft complete | [Empirical Results](CHAPTER_5_EMPIRICAL_RESULTS.md) |
| Write Chapter 6 | Draft complete | [Discussion and Limitations](CHAPTER_6_DISCUSSION_LIMITATIONS.md) |

PR-AUC means average precision. Headline false alarms / 1k means `1000 × FP / legitimate rows`; JSON and CSV also retain the all-row denominator. Model and threshold provenance, features, package versions, and input hashes are recorded in the manifest. The receipt hashes final outputs. Cached probabilities are retained locally as `reports/final/predictions.npz`.

No artifact reaches 85% test recall. Random Forest F0 has the largest F1 score (0.800000), detecting 38 frauds with five false alarms and 73.08% recall. The largest AP is 0.781033 for Random Forest SMOTE. These observations do not select a new deployed model.

The chapters disclose prior test exposure, limited positive-class support, unequal F0/F1 threshold policies, missing load measurements, and offline/service preprocessing differences. An untouched-test claim needs genuinely independent later data and cannot be recovered by rescoring this partition.

## Reuse and verification

The [evaluator](../scripts/evaluate_frozen_creditcard.py) refuses to run if `reports/final` exists, including after interruption. Keep the directory and use cached outputs for further analysis; do not remove the receipt to obtain another final run.

The [synthetic tests](../tests/test_frozen_evaluation.py) verify metric denominators, inclusive thresholds, invalid-score rejection, the repeat-run guard, manifest timing, cached predictions, and output hashes. Six tests passed. They do not read the research holdout.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_frozen_evaluation.py -q
```
