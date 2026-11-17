import http from 'k6/http';
import { check } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// Run one VU level at a time so each summary has an unambiguous load level.
const vus = Number(__ENV.VUS || 10);
if (![10, 50, 100, 250].includes(vus)) throw new Error('VUS must be 10, 50, 100, or 250');
const base = (__ENV.BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
const model = __ENV.MODEL || 'xgboost';
if (!['xgboost', 'random_forest'].includes(model)) throw new Error('Unsupported MODEL');
const duration = __ENV.DURATION || '2m';
const payload = { Time: 86400, Amount: 25 };
for (let i = 1; i <= 28; i++) payload[`V${i}`] = 0;
const body = JSON.stringify(payload);
const params = { headers: { 'Content-Type': 'application/json' }, timeout: __ENV.REQUEST_TIMEOUT || '60s' };

const inference = new Trend('t_inf_ms', true);
const explanation = new Trend('t_shap_ms', true);
const total = new Trend('t_total_ms', true);
const failed = new Rate('transaction_failure_rate');
const completed = new Counter('transactions_completed');

export const options = {
  scenarios: { sustained: { executor: 'constant-vus', vus, duration, gracefulStop: '60s' } },
  summaryTrendStats: ['count', 'avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  thresholds: {
    t_total_ms: ['p(95)<100'],
    transaction_failure_rate: ['rate<0.01'],
  },
};

export default function () {
  const start = Date.now();
  const prediction = http.post(`${base}/api/v1/predict?model=${model}`, body, { ...params, tags: { endpoint: 'predict' } });
  inference.add(prediction.timings.duration);
  const okPrediction = check(prediction, { 'prediction succeeds': (r) => r.status === 200 });
  if (!okPrediction) { failed.add(1); return; }

  const explanationResponse = http.post(`${base}/api/v1/explain?model=${model}&top_n=3`, body, { ...params, tags: { endpoint: 'explain' } });
  explanation.add(explanationResponse.timings.duration);
  const okExplanation = check(explanationResponse, { 'explanation succeeds': (r) => r.status === 200 });
  total.add(Date.now() - start);
  failed.add(!okExplanation);
  if (okExplanation) completed.add(1);
}

export function handleSummary(data) {
  return {
    stdout: JSON.stringify({ vus, model, duration, metrics: data.metrics }, null, 2),
    [`reports/load-tests/k6_${model}_${vus}vu.json`]: JSON.stringify(data, null, 2),
  };
}
