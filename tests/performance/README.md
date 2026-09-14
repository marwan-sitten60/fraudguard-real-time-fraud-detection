# Local benchmark protocol

No final-model latency result is claimed. k6 is an external developer tool.

Reference environment: Linux/WSL2 Docker, 4 dedicated logical CPUs, 8 GB memory,
API one worker, constant MOCK model, mock features, no reverse proxy, client on the
same machine. Run Compose with all seven services so background scraping is present.
Record actual CPU model, OS, Docker version, available RAM, image IDs, git revision,
feature mode and power settings. If different, report a different environment.

Start the stack, verify readiness, then `k6 run tests/performance/scoring.js`.
The script warms up at 5 VUs for 15 s, then measures 20 VUs for 60 s. It reports and
exports p50/p95/p99 client latency, request rate and semantic error rate. Measured throughput is the tagged request count divided by the 60-second window;
requests finishing during graceful shutdown can slightly bias that estimate. Use
Prometheus over the same window for server-observed throughput.

`WARMUP_DURATION`, `DURATION`, and `VUS` may shorten a script smoke check. By default,
only semantic error rate and non-empty traffic are hard gates. Set
`ENFORCE_LATENCY_SLO=true` only in an environment approved for server-SLO comparison;
the client threshold remains a conservative proxy and must be reported as such.
These are closed-loop VUs, not a claim of sustained arrival-rate capacity.

Server p95 query (select only the measured time interval):

```promql
histogram_quantile(0.95, sum by (le) (
  rate(fraudguard_http_request_duration_seconds_bucket{
    route="/api/v1/transactions/score",method="POST"}[1m])
))
```

Use 0.50 and 0.99 for other percentiles. Histogram quantiles are bucket approximations.
Throughput: `sum(rate(fraudguard_http_requests_total{route="/api/v1/transactions/score"}[1m]))`.
Error fraction: same rate with `status=~"4..|5.."` divided by all scoring responses.
Monitor errors and dropped iterations, CPU and memory alongside latency. Repeat three
times without changing configuration and report variation; do not cherry-pick a run.
The response's `latency_ms` excludes API validation/serialization, and k6 includes
network overhead. Neither can replace full server timing. Real Redis and future model
benchmarks require their own workload, cardinality, cold-start and failure scenarios.
