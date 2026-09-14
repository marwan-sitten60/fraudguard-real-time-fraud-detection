# ADR-004: Single-broker Redpanda for local development

## Status
Accepted for Phase 1.

## Context
Future scoring events will feed storage, feature updates and training. A developer laptop should not require a multi-node Kafka installation.

## Decision
Provision one Redpanda broker and define strict version-1 event envelopes, publisher and handler ports. Include standalone bounded memory/no-op adapters only.

## Alternatives Considered
Kafka is a viable later transport. Direct database writes couple request serving to storage; claiming durable delivery via background tasks is unacceptable.

## Consequences
Local Kafka-compatible infrastructure exists, but the score route emits no broker events. Consumer deduplication, retries, backpressure and durability require a later phase. One broker provides no HA.
