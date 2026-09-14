# FraudGuard system design ? Phase 1

## Goals and scope

Build one explainable, testable backend before introducing real model complexity.
Phase 1 runs end to end with a constant MOCK predictor, not fraud protection. The
backend is a modular monolith; infrastructure services are separate containers.

## Latency SLO and measurement

Target server-side p50 <30 ms, p95 <100 ms and p99 <150 ms, measured in the pinned
local environment described in `tests/performance/README.md`. This is not a guarantee.
An initial planning budget is validation/HTTP 10 ms, features 20 ms, rules 5 ms,
predictor 30 ms, policy/serialization 10 ms and 25 ms headroom at p95. Component
percentiles do not add mathematically; the real end-to-end benchmark decides.

`fraudguard_http_request_duration_seconds` spans receipt/reading of the ASGI body
through final response send and includes validation. It excludes pre-ASGI socket
queueing, network and proxy time. `latency_ms` and scoring histogram measure the
application service only. k6 measures client duration, so its output is not the
server-side SLO. Report all three and resource/concurrency settings.

## Synchronous path and boundaries

HTTP -> bounded body / correlation middleware -> Pydantic validation -> domain
Transaction -> ScoringService -> FeatureProvider -> RuleEngine -> in-memory FraudModel
-> DecisionPolicy -> FraudScore -> response schema -> HTTP.

`domain` uses only stdlib; protocols describe interchangeable boundaries. API owns
FastAPI, middleware and mapping. Features own Redis IO; models own serving adapters.
The composition root (`api/app.py`) builds instances once per lifespan.
Compared with the suggested tree, there is no duplicate `models/interfaces.py`,
`features/service.py` forwarding wrapper or `decision/engine.py` wrapper: the domain
ports, ScoringService and concrete policy already own those responsibilities. Rules
stay in one small engine until enough rules justify splitting a rule catalog.
Future training entry points are documented reservations, not functions that pretend
to train or evaluate. The application
service coordinates steps and instruments them, but contains no transport or database
code. Threshold policy uses only domain data. Country mismatch is an illustrative
reason code, not a calibrated risk signal. MONITOR/CHALLENGE are reserved enum values.

No registry lookup, disk model load, SQL, Kafka acknowledgement, training, SHAP or
heavy intelligence runs in a scoring request. The mock predictor is synchronous and
constant-time. Before adopting a real CPU predictor, measure event-loop blocking,
thread safety and bounded executor/native-thread settings; an async route does not
make CPU work asynchronous. Model loading remains once per worker.

## Asynchronous path and events

Version-1 typed envelopes exist for transaction.created, transaction.scored,
transaction.reviewed and fraud.confirmed. Envelopes have event ID, event type,
version, timezone-aware timestamp, correlation ID and typed payload. Unknown versions
are rejected; incompatible changes require a new schema and consumer compatibility
plan. Future consumers deduplicate by event_id, persist, update features and feed
training. Partitioning should use the relevant entity key for ordered updates.

Phase 1 deliberately does NOT publish from scoring or persist requests. The no-op and
bounded in-memory publisher are standalone development adapters, not delivery guarantees.
Redpanda has no producer integration yet. A future bounded asynchronous handoff must
expose overflow/drop metrics and shutdown draining; a durable ingestion/outbox design
must explicitly reconcile no broker roundtrip with audit requirements. In-process
background tasks alone do not provide durable delivery. Do not claim exactly-once
scoring or use this phase for audited payments. Duplicate transaction IDs are scored
again; idempotency/persistence semantics are deferred.

## Storage choices

PostgreSQL is the eventual transaction/decision/label system of record. Alembic creates
three tables with exact NUMERIC money, timezone-aware timestamps, basic checks and
transaction lookup indexes. Multiple decisions/labels per transaction allow future
re-scoring and label history. No ORM models/repositories are invented before consumers
exist. Use explicit migrations now; ORM autogeneration is not configured.

Redis is an optional low-latency snapshot reader, not a durable record. The mock mode
is independent of Redis. Redis mode fetches one versioned JSON user snapshot with a
20 ms overall deadline, a socket deadline, explicit version validation and freshness
checks. Missing, invalid, stale or future-dated snapshots fail closed with 503. A
Redis ping only establishes connectivity; readiness cannot validate all future users.
The example feature mapping is not a final model feature contract.

MLflow runs locally with SQLite metadata and a shared persistent artifact directory.
It is isolated from transaction Postgres to reduce setup and migration coupling. Move
to PostgreSQL/object storage before concurrent shared training or multiple tracking
replicas. Registry access belongs to training/deployment startup, never scoring.

## Feature architecture

Offline code will generate point-in-time historical snapshots keyed by entity and
feature version, using event time, late-data policy and training cutoffs. Keep feature
logic under src; notebooks only inspect it. Online materialization and streaming
updates must implement the same definitions and validate freshness, null handling,
ordering and schema hashes. Feast is a potential implementation of FeatureProvider,
not a current dependency. Historical replay must not use current online state.

Behavioral aggregates, anomaly scores, graph and sequence intelligence can be
precomputed with explicit freshness and missingness contracts. Do not add expensive
per-request inference without measurement and a deliberately approved fallback policy.

## Model architecture and deployment

Only MockFraudModel is supported. MODEL_NAME/MODEL_ALIAS reserve registry identity;
they do not change the constant result. A future loader resolves an immutable model
version, verifies checksums, trusted serialization, feature signature and quality gates,
loads/warmups it, then marks readiness. Rollback uses a previously validated artifact.
Already loaded workers do not depend on registry availability. A startup artifact
failure must not silently select a mock or approve fallback. Phase 1 startup exceptions
abort lifespan; runtime not-ready/invalid predictions produce sanitized 503s.

## Observability and security

JSON logs allow-list event names, request ID, app/model versions, decision, bounded route,
status and latency; never log transaction bodies, user/device/transaction IDs, secrets
or exception strings. Request IDs allow only 1?64 alphanumeric/underscore/hyphen characters;
untrusted invalid IDs are replaced. Propagate this context to future event envelopes.
Prometheus uses route templates (unknown paths -> unmatched), a bounded HTTP method set,
status and decision. No request/entity IDs or arbitrary model versions in metric labels.
Grafana provisions a datasource and p95/throughput/error panels. No drift alerts exist yet.

A 16 KiB body bound is enforced against both declared and streamed length. Pydantic
rejects unknown fields and fractional float money; callers send decimal strings.
Safe errors avoid echoing raw inputs. CORS is explicit/configurable. Container API runs
as UID 10001, one worker, no dev dependencies. Hash-locked dependency installation is
separate from pinned image tags; tags are not content-addressed digests. Refresh and
scan images before release. Lockfiles provide reproducibility, not vulnerability proof.
A future ingress must add authentication, TLS, rate limits, body-read deadlines and
concurrency limits. The local stack is loopback-bound and has no production IAM.

## Failure strategy

| Failure | Serving behavior | Recovery/limits |
|---|---|---|
| Redis down in mock mode | no effect | Redis not required by selected provider |
| Redis down in redis mode | ready=503; score=503 | bounded IO; no implicit defaults |
| Required snapshot missing/stale | score=503 | readiness ping may still pass; reseed example |
| Model absent at startup | lifespan fails | deploy/restart validated artifact later |
| Model not ready/errors/invalid score | ready reflects flag; score=503 | error metric; no fallback |
| PostgreSQL down | scoring works; migrations/consumers fail | no persistence guarantee in Phase 1 |
| Broker down | scoring works | no publishing exists; future delivery/backlog policy required |
| MLflow down | loaded model unaffected | future new deployments fail without artifact |

`/health` reports process health; `/ready` checks selected serving model and feature
provider. PostgreSQL, broker and MLflow must not gate readiness. Errors are logged and
counted without disclosing internal exception text. A 503 is an unavailable decision,
not BLOCK/APPROVE; the payment orchestrator must define its own risk-safe handling.

## Future scaling

First benchmark one worker and profile. Scale stateless API containers horizontally,
size connection pools, cap CPU threads and define backpressure. One process per
container keeps Prometheus aggregation simple. Extract consumers/training processes
when workload isolation requires it; do not split internal modules into microservices.
Introduce replication, durable event handling, model promotion/rollback, online/offline
parity and deployment automation only with measured requirements. No Kubernetes,
cloud, scheduler or full feature-store choice is required in this phase.

## Infrastructure references

Compose configuration follows the [Redpanda single-broker example](https://docs.redpanda.com/labs/docker-compose/single-broker/)
and [MLflow self-hosted tracking documentation](https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/).
These describe the infrastructure patterns, not verification of this project's stack.
