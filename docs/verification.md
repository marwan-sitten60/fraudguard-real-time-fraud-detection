# Phase 1 verification

Verified on 2026-09-14 using Python 3.12.13, Docker Desktop on Windows/WSL2,
Docker Engine 29.3.1, Docker Compose 5.1.1, and k6 1.0.0.

## Quality and tests

- `ruff format --check .`: 89 files formatted.
- `ruff check .`: passed.
- `mypy`: strict mode passed for 51 source files.
- `pytest`: 71 unit/contract tests passed, 2 integration tests deselected, 0 failed,
  95% branch-aware coverage.
- `pytest -m integration tests/integration --no-cov`: 2 passed against Compose
  PostgreSQL and Redis.
- Docker image build: passed. Runtime UID/GID is 10001 and pytest, Ruff, mypy, and
  Hatchling are absent from the runtime image.

The test environment emitted two upstream deprecation warnings from the current
FastAPI/Starlette TestClient stack. They do not affect test outcomes and are not
suppressed globally.

## Services and contracts

`docker compose up -d --build` completed. API, PostgreSQL, Redis, Redpanda, MLflow,
Prometheus, and Grafana reported healthy. The one-shot migration container exited 0.
Alembic reported `0001 (head)` and PostgreSQL contained `transactions`,
`fraud_decisions`, and `fraud_labels` plus `alembic_version`.

Redis passed a real write/read adapter round trip. Redpanda's `rpk cluster health`
reported healthy with no down nodes, leaderless partitions, or under-replicated
partitions. MLflow `/health` returned 200. Prometheus reported its FraudGuard target
`up` at `http://api:8000/metrics`. Grafana reported a healthy database and reached
the provisioned Prometheus service.

Dockerized `/health`, `/ready`, `/metrics`, and `/api/v1/transactions/score` returned
successful responses. The score contract contained transaction ID, risk score,
decision, reason codes, model version, and latency, and identified `mock-v1`.
Invalid input returned 422; an over-limit body returned 413; missing required Redis
features returned a sanitized 503. Unit/contract tests also exercise runtime model
failure and model-not-ready behavior. Scoring remained available while MLflow and
Redpanda were deliberately stopped, and both containers were restarted afterward.

## Performance foundation

The standard 15-second warmup and 60-second measured run at 20 VUs produced the
following **Phase 1 mock-pipeline client baseline**:

- p50: 32.69 ms
- p95: 132.82 ms
- p99: 222.55 ms
- measured throughput: 420.05 requests/second
- semantic error rate: 0%

This run crossed the future client-side proxy thresholds. It does not satisfy or
disprove the future server-side production SLO because it includes Docker networking,
client scheduling, development logging, and a Windows/WSL2 environment. The k6 script
now treats latency enforcement as opt-in and always enforces semantic error rate and
non-empty traffic. A subsequent 1-second warmup/3-second measured script smoke at 3
measured VUs exited 0 and reported p50 17.06 ms, p95 34.85 ms, p99 44.62 ms,
123.83 requests/second, and 0% semantic errors. Short smoke numbers are script
validation only, not capacity evidence.

## Verification boundaries

The GitHub Actions workflow was inspected locally but cannot be executed as a hosted
workflow because this workspace is not a Git repository and has no GitHub remote.
Its constituent Ruff, mypy, pytest, integration, migration, image-build, and container
smoke commands were exercised locally. Image tags are pinned by version but most are
not digest-pinned. The Compose stack is a loopback-bound developer simulation and has
no production authentication, TLS, high availability, or durable event pipeline.
