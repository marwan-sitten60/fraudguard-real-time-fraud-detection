# Phase 4: online feature serving

## Contract and request path

`fraud-online-features-v1` contains transaction-time fields and label-free customer and merchant history. Redis stores one versioned JSON snapshot per entity under `fraudguard:features:v1:{entity}:{id}`. A request performs two concurrent Redis `GET` commands, validates both snapshots, merges the historical values, and assembles transaction-time features in process.

The deterministic historical backfill replays transactions in event-time and transaction-ID order. It uses only rows strictly before the requested cutoff. The expanded parity test compared 30 transactions across five customers, four merchants, different event times, and increasingly warm histories. It found 0 mismatches across 12 comparable features; the maximum absolute numeric difference was 0.0 at a `1e-12` assertion tolerance. First-seen entities are covered by the explicit missing-snapshot failure policy rather than fabricated defaults.

## Failure behavior

Redis connection and timeout errors become controlled `FeatureUnavailable` errors. Missing customer or merchant snapshots, malformed JSON, a wrong contract version, a wrong entity ID, stale or future-dated timestamps, and missing required fields also fail closed. No fraud-safe fallback has been defined. The scoring service returns a controlled service failure when this provider is selected and required features cannot be obtained.

## Metrics

The production Redis provider records `fraudguard_feature_fetch_duration_seconds`, `fraudguard_feature_fetch_errors_total`, `fraudguard_feature_snapshot_stale_total`, and `fraudguard_feature_missing_total`. These metrics have no labels, which prevents transaction, customer, merchant, and device identifiers from creating high-cardinality series.

## Configuration and API status

`FEATURE_BACKEND=redis_v1` selects the production snapshot provider during application lifespan construction. `FEATURE_BACKEND=mock` remains the default, and the earlier Redis development adapter remains available as `redis`. Model construction is unchanged: `MODEL_BACKEND` accepts only `mock`, and the API continues to report `model_version=mock-v1`.

`merchant_prior_fraud_count` and `merchant_prior_fraud_rate` are deliberately excluded because real fraud labels arrive after transaction time. The Phase 3 XGBoost artifact expects a different offline feature contract and is incompatible with this online contract. It must not be loaded or deployed until a later phase defines a production-safe, matching feature set and retrains it.

## Local latency baseline

On 2026-09-15, the repeatable benchmark ran 1,000 requests at concurrency 20 against the Compose Redis container. Each request issued two concurrent Redis reads.

| Segment | p50 | p95 | p99 |
| --- | ---: | ---: | ---: |
| Redis retrieval and snapshot validation | 7.158 ms | 20.425 ms | 47.744 ms |
| In-process feature assembly | 0.0009 ms | 0.0010 ms | 0.0011 ms |
| Combined online feature path | 7.339 ms | 27.515 ms | 61.784 ms |

These figures are a local Phase 4 feature-path baseline. They do not measure the HTTP scoring path or prove the production latency SLO.
