# ADR-001: Modular monolith in a monorepo

## Status
Accepted for Phase 1.

## Context
One junior engineer needs to evolve API, ML training and feature contracts together before load justifies separate services.

## Decision
Use src/fraudguard for all production Python, isolated infrastructure containers and a reserved frontend directory. Keep standard-library domain contracts.

## Alternatives Considered
Independent microservice repos increase deployment and compatibility work; notebook-centric code prevents reliable reuse.

## Consequences
Atomic contract changes and one quality pipeline are simple. Internal import discipline matters; independently scaling training/consumers later may require separate entry points.
