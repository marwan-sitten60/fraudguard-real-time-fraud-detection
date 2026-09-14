import http from 'k6/http';
import { check } from 'k6';
import { Rate } from 'k6/metrics';

const failures = new Rate('scoring_errors');
const sample = JSON.parse(open('../../scripts/sample-transaction.json'));
const base = __ENV.BASE_URL || 'http://localhost:8000';
const warmupDuration = __ENV.WARMUP_DURATION || '15s';
const measuredDuration = __ENV.DURATION || '60s';
const measuredVus = Number(__ENV.VUS || 20);
const thresholds = {
  'scoring_errors{phase:measured}': ['rate<0.01'],
  'http_reqs{phase:measured}': ['count>0'],
  // Materialize the measured-only trend for handleSummary without enforcing an SLO.
  'http_req_duration{phase:measured}': ['max>=0'],
};
if (__ENV.ENFORCE_LATENCY_SLO === 'true') {
  // Opt-in only: k6 is client-observed latency, while the target is server-side.
  thresholds['http_req_duration{phase:measured}'] = ['p(50)<30', 'p(95)<100', 'p(99)<150'];
}
export const options = {
  scenarios: {
    warmup: { executor: 'constant-vus', vus: 5, duration: warmupDuration,
      gracefulStop: '0s', exec: 'score', tags: { phase: 'warmup' } },
    measured: { executor: 'constant-vus', vus: measuredVus, duration: measuredDuration,
      startTime: warmupDuration, exec: 'score', tags: { phase: 'measured' } },
  },
  summaryTrendStats: ['avg', 'med', 'p(50)', 'p(95)', 'p(99)', 'max'],
  thresholds,
};
export function score() {
  const payload = { ...sample, transaction_id: `bench_${__VU}_${__ITER}` };
  const response = http.post(`${base}/api/v1/transactions/score`, JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json' }, tags: { name: 'score' }, timeout: '2s',
  });
  const ok = check(response, {
    '200 MOCK response': r => r.status === 200 && r.json('model_version') === 'mock-v1',
  });
  failures.add(!ok);
}
export function handleSummary(data) {
  return {
    'benchmark-results.json': JSON.stringify(data, null, 2),
    stdout: JSON.stringify({
      measured_latency_ms: data.metrics['http_req_duration{phase:measured}'].values,
      measured_error_rate: data.metrics['scoring_errors{phase:measured}'].values,
      measured_requests: data.metrics['http_reqs{phase:measured}'].values.count,
      measured_requests_per_second:
        data.metrics['http_reqs{phase:measured}'].values.rate,
    }, null, 2) + '\n',
  };
}
