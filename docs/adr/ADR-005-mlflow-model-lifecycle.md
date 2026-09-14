# ADR-005: MLflow outside the request path

## Status
Accepted for Phase 1.

## Context
Reproducible experiments and promotion need registry metadata, but model download on every request is incompatible with latency and availability goals.

## Decision
Reserve ModelRegistry and lifespan loading. Run MLflow with persistent SQLite metadata and artifact storage for a single local instance. Only load MockFraudModel now.

## Alternatives Considered
Per-request registry access is too slow and fragile. PostgreSQL/object-store MLflow can wait until shared concurrent training. No hand-built registry.

## Consequences
Loaded models remain available if MLflow fails. Future startup needs artifact verification and quality gates. Local SQLite is not a multi-replica backend; name/alias config is preparatory.
