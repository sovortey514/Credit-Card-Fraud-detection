# Week 17: prediction and explanation load test

## Offline and replay consistency

The local consistency test `tests/test_offline_replay_consistency.py` compares
the first 30 chronological test transactions for each saved Random Forest and
XGBoost model. It initializes replay with train and validation amount history,
compares the replay service's ML probabilities with predictions from the saved
offline feature table, and checks how high-severity rules can affect the final
route. Both model cases passed in the local environment. This is a limited
service-level check, not an HTTP, full-dataset, or independent holdout evaluation;
SHAP and history persistence are disabled in the test. The test partition had
already been exposed during development, as documented in the final manifest.

## Local functional checks

The API, replay, and prediction-history integration tests passed (7 tests),
and the React dashboard production build succeeded. These checks exercise the
application components but do not establish a complete interactive browser
workflow or system performance under load. The `k6` command was not available
on PATH in the local environment, so the load test below was not run.

Start the fraud API with the same model artifacts and configuration intended for the benchmark. Install k6, create `reports/load-tests`, and run each sustained level separately from the repository root:

```powershell
New-Item -ItemType Directory -Force reports/load-tests
$env:DURATION = '2m'
foreach ($level in 10, 50, 100, 250) {
  $env:VUS = "$level"
  k6 run load-tests/creditcard.js
}
```

Optional variables: `BASE_URL` (default `http://localhost:8000`), `MODEL` (`xgboost` or `random_forest`), and `REQUEST_TIMEOUT` (default `60s`). Use representative, non-sensitive input and document hardware, software versions, model, API workers, environment, duration, and other concurrent load. The included fixed synthetic 30-feature payload gives repeatable requests but does not represent the full transaction distribution.

Each iteration sends `/api/v1/predict` followed by `/api/v1/explain`. `t_inf_ms` is the prediction HTTP request duration; `t_shap_ms` is the explanation HTTP request duration, including preprocessing and prediction performed by that endpoint. `t_total_ms` measures the wall-clock duration of both sequential requests, including connection overhead. Percentiles are client-observed and cannot be interpreted as isolated server inference or SHAP computation. Failed prediction attempts do not produce a total sample; inspect `transaction_failure_rate` and checks alongside all latency statistics. The SLO is assessed on successful prediction attempts that reached the explanation request, with a separate failure threshold below 1%. A completed transaction requires both responses to succeed.

The k6 summary records median (P50), P90, P95 and P99, plus `transactions_completed` rate. Compare the successful transaction rate, error rate, and P95 across sustained levels; each transaction makes two HTTP requests. Record the highest observed sustainable throughput meeting both thresholds and identify the first load where throughput plateaus, errors rise, or P95 exceeds the SLO. These are closed-loop VU tests, not fixed-arrival-rate tests, so they show observed saturation only within the tested levels; use an arrival-rate sweep for a more precise saturation point. Include warm-up and repeat runs when drawing conclusions.

**Results:** Not yet measured. P95 compliance and maximum RPS cannot be established without a successful run against the target deployment.
