# Research roadmap (20 weeks)

| Weeks | Phase | Evidence / output |
|---|---|---|
| 1–4 | Data collection, EDA, preprocessing | Dataset audit, chronological splits, leakage register |
| 5–8 | Feature engineering | Baseline features, causal historical features, comparison |
| 9–12 | Model comparison | Logistic Regression, Random Forest, XGBoost; validation threshold; held-out test |
| 13–16 | Backend and replay | FastAPI prediction, validation, replay script, streaming integration |
| 17–18 | Dashboard | React monitoring, live event updates, alerts |
| 19–20 | Testing and thesis | API latency/throughput, error analysis, limitations, defense |

## Research safeguards
- PaySim is synthetic, not real Cambodian bank/KHQR data.
- Pre-transfer fields only; post-transaction balances are not inputs.
- Keep test partition untouched until selection and threshold tuning are complete.
- Never claim a risk score is confirmed fraud.
- The initial dashboard supports manual scoring; streaming and behavioral aggregates are future work.
