# Credit-card fraud research roadmap

| Phase | Work | Evidence / output |
|---|---|---|
| Data and EDA | Audit the ULB credit-card dataset and inspect imbalance, time, amount, and PCA features | EDA summaries and provenance hash |
| Preprocessing | Chronological train/validation/test split; fit scaling on training only | Parquet partitions and leakage audit |
| Feature engineering | Compare F0 with engineered temporal, amount, and interaction features | Feature metadata and tests |
| Model comparison | Logistic Regression, Random Forest, and selected baselines | TimeSeriesSplit results and validation PR/ROC curves |
| Explainability | Generate SHAP explanations and assess limitations | Explanation examples and methodology |
| Application | Serve predictions and display monitoring information | API, dashboard, integration checks |
| Thesis | Document methods, results, limitations, and defense | Thesis chapters and reproducibility evidence |

## Research safeguards

- Keep partitions chronological and do not use the held-out test set for model selection or threshold tuning.
- Fit learned preprocessing statistics only on the training partition.
- Treat `V1`–`V28` as anonymized PCA components; their original meanings are unavailable.
- The dataset has no card-present/card-not-present field, so CNP-specific performance cannot be evaluated from these records.
- Do not describe model scores as confirmed fraud or calibrated real-world probabilities.
