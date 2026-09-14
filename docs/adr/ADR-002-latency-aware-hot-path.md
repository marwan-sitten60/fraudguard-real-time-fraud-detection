# ADR-002: Keep scoring latency measurable and bounded

## Status
Accepted for Phase 1.

## Context
FraudGuard targets p95 server handling below 100 ms; broker, registry and analytical SQL latency would consume unpredictable portions of that budget.

## Decision
Read online snapshots with a deadline, evaluate lightweight rules and a startup-loaded model, then apply policy. No persistence or broker calls in Phase 1 scoring.

## Alternatives Considered
Synchronous publish/write would improve acknowledged capture but add dependency latency. Background tasks alone would disguise event loss.

## Consequences
API can operate without storage/broker. Phase 1 has no durable audit or idempotency; future durable ingestion needs an explicit design. Measure full HTTP timing, not just prediction.
