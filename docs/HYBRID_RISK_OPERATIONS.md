# Hybrid fraud-risk operations

The application now combines a calibrated machine-learning probability with a
stateful deterministic rule layer. The model remains responsible for learning
fraud patterns from the anonymized `Time`, `Amount`, and `V1`–`V28` features;
the rule layer adds operational context that is not present in the Kaggle ULB
dataset.

## Runtime decision flow

1. The API validates the transaction and accepts optional `account_id`,
   `card_id`, country, proxy, and device metadata.
2. The preprocessing pipeline produces the model feature vector.
3. The scoring service computes `ml_probability` and TreeSHAP contributors.
4. The velocity engine tracks 1-minute, 10-minute, and 1-hour counts and spend
   for the account/card key. The local implementation is in-memory; a
   production deployment can replace it with Redis while preserving the API.
5. Deterministic rules evaluate rapid bursts and amount spikes relative to the
   rolling one-hour average.
6. The combined result is routed as `approve`, `step_up`, or `flag`:
   - `approve`: probability below the low threshold and no material rule hit.
   - `step_up`: gray-zone probability or a medium-severity rule hit.
   - `flag`: probability at or above the calibrated threshold or a high-severity
     velocity rule hit.
7. The response and replay event include the ML score, route, velocity context,
   triggered rules, and top SHAP contributors.

## Analyst audit flow

Flagged and step-up cases can be reviewed from the dashboard. An analyst can
record `APPROVED`, `CONFIRMED_FRAUD`, or `ESCALATED`, together with reviewer ID,
timestamp, and notes. Prediction metadata, rule evidence, and SHAP contributors
are retained in SQLite so the decision can be audited later.

This is an operational prototype rather than a claim that the anonymized ULB
dataset contains real BIN, IP, device, or account-history signals. Those fields
are optional API enrichment points for a production integration.
