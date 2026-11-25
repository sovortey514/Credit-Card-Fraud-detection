# Four-week literature review protocol

## Objective and scope

Identify and critically compare methods for transaction fraud detection across five themes: class imbalance; temporal leakage and delayed labels; metaheuristic hyperparameter tuning; explainability and TreeSHAP; and real-time serving. The review informs defensible baselines and experimental design for the ULB credit-card dataset; it does not establish performance on live money-transfer data or on card-not-present transactions.

## Search and selection

Search Google Scholar, Scopus or Web of Science where available, IEEE Xplore, ACM Digital Library, and publisher sites. Include foundational works without a lower date limit and search recent publications through the date of the review. Record the date, database, exact query, filters, number of results, and export location for every search; deduplicate by DOI and title. Follow relevant citation and reference chains.

Use combinations of these searches, adapting syntax to each database:

1. `("fraud detection" OR "credit card fraud") AND ("class imbalance" OR SMOTE OR "class weighting")`
2. `("fraud detection" OR transactions) AND ("temporal validation" OR "data leakage" OR "delayed labels" OR "concept drift")`
3. `("fraud detection" OR "credit card fraud") AND ("genetic algorithm" OR metaheuristic) AND ("hyperparameter optimization" OR tuning)`
4. `("fraud detection" OR "tree ensembles") AND (SHAP OR TreeSHAP OR explainability)`
5. `("fraud detection" OR "transaction scoring") AND ("real time" OR latency OR serving OR deployment)`

Include English-language peer-reviewed research and foundational primary method papers that address at least one theme and describe a reproducible method or relevant deployment evidence. Mark preprints and credible technical reports separately where peer-reviewed operational evidence is scarce. Exclude duplicates, inaccessible full texts (record them separately), work unrelated to fraud or transferable methods, and papers without enough methodological detail to assess their claims. Screen titles and abstracts first, then full text against these criteria; record reasons for full-text exclusions. One reviewer performs screening, with a second reviewer consulted when available for ambiguous cases. Do not represent this protocol as a completed systematic review.

For each included study, capture citation and link, theme, data and class prevalence, split and leakage controls, methods and comparators, metrics and operating thresholds, results, limitations, and relevance to this project in the [matrix](LITERATURE_MATRIX.md). Mark information not checked or not reported instead of guessing. Extract numerical results only after checking the full text, tables, and evaluation protocol.

## Schedule and deliverables

| Week | Activities | Deliverables |
|---|---|---|
| 1 | Run and log searches across all five themes; deduplicate and screen titles and abstracts. | Search log, candidate bibliography, initial screening decisions. |
| 2 | Screen full texts; extract datasets, metrics, baselines, and limitations for imbalance and temporal validation. | Full-text decisions and updated matrix. |
| 3 | Extract metaheuristic, XAI, and serving evidence; check methodological comparability and leakage safeguards. | Updated matrix and baseline/tuning comparison notes. |
| 4 | Synthesize evidence by theme, identify conflicting findings and gaps, and revise the chapter and references. | Completed matrix, narrative synthesis, search and screening counts, and documented research decisions. |

## Quality and synthesis rules

Assess temporal ordering, split before preprocessing or resampling, label availability, tuning on training/validation only, class prevalence, baseline fairness, compute budget and random seeds, metric definitions, and reproducibility. For serving, record whether latency is measured end-to-end, including hardware, workload, concurrency, failures, and percentiles. Distinguish local explanation fidelity from causal explanation. Compare numbers only when datasets, splits, and metrics are compatible. Summarize unresolved questions and threats to validity, including the current project's previously exposed test partition. The schedule is a plan, not evidence that four weeks of searching or screening have already occurred.
