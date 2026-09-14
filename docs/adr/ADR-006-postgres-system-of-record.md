# ADR-006: PostgreSQL with explicit migrations

## Status
Accepted for Phase 1.

## Context
Future investigation and labels require durable relational history with exact money and versioned decisions, without analytical work in scoring.

## Decision
Create transactions, fraud_decisions and fraud_labels using reversible Alembic migrations. Provide a connection adapter and future repository port, no scoring writes.

## Alternatives Considered
Redis lacks the intended relational/audit role. Schemaless payload-only storage hides contracts. A complete repository implementation before consumers exist adds unused code.

## Consequences
Schema is reviewable and integration-testable. API success does not imply persistence. Consumers must later define replay, uniqueness, retention and privacy rules. MLflow metadata remains isolated.
