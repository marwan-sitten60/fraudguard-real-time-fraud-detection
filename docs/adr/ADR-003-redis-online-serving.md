# ADR-003: Redis behind a feature provider

## Status
Accepted for Phase 1.

## Context
Future behavioral/precomputed signals need low-latency retrieval while historical training needs point-in-time correctness.

## Decision
Provide mock and Redis snapshot adapters behind FeatureProvider. Use version/freshness checks, TTL in sample seed, and controlled 503 on unusable required features. Default is mock.

## Alternatives Considered
Postgres analytical reads violate the intended request budget. Feast now would add setup without a defined real feature contract.

## Consequences
Redis mode adds a critical dependency and needs operational limits. The example JSON map is not Feast or a full feature store; shared definitions/parity remain future work.
