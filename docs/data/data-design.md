# Phase 2 data design

## Provenance boundaries

FraudGuard has two deliberately separate data products.

| Product | Source | Purpose | Must not be confused with |
|---|---|---|---|
| Historical benchmark data | Fraud Detection Handbook simulated-data-raw | Future offline research | Real banking data or simulator traffic |
| Operational simulator data | FraudGuard deterministic generator | Demo, load, and behavioral development | Handbook historical rows |

The handbook dataset is public simulated benchmark-style data, not production banking
activity. Its documented required columns are `TRANSACTION_ID`, `TX_DATETIME`,
`CUSTOMER_ID`, `TERMINAL_ID`, `TX_AMOUNT`, and binary `TX_FRAUD`. Published daily
batches can additionally contain `TX_TIME_SECONDS`, `TX_TIME_DAYS`, and
`TX_FRAUD_SCENARIO`; the adapter does not depend on these extensions. The handbook
describes `TERMINAL_ID` as a merchant/terminal identifier. Source material:
[handbook simulator](https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_3_GettingStarted/SimulatedDataset.html)
and [published raw batches](https://github.com/Fraud-Detection-Handbook/simulated-data-raw).

## Canonical historical schema

`historical-transaction-v1` contains only source-supported business fields:

```text
transaction_id, event_time, customer_id, merchant_id, amount, fraud_label,
source, schema_version, label_available_time
```

There is no currency, country, device, IP address, card number, payment channel, or
merchant category in this canonical historical schema because the selected source does
not provide them. Amount is a `Decimal` in Python and a decimal string in Parquet to
avoid binary floating-point changes. The source's timezone-naive `TX_DATETIME` is interpreted
as UTC by the adapter and recorded as timezone-aware UTC. This is an explicit pipeline
assumption, not a claim about the source's real-world timezone.

The Phase 1 serving request remains separate. Its device/country/channel fields are
provided only by FraudGuard's synthetic operational simulator. The simulator converts
to the unchanged `TransactionRequest` contract through `SimulatedTransaction.request`.

## Time and labels

- **event_time**: when the transaction occurred; all split and future feature work use it.
- **processing_time**: when FraudGuard prepares an event; represented by manifest generation
  time, not inferred from historical rows.
- **label_available_time**: when fraud could become known operationally. It is `null` for
  the handbook source because the source exposes a final label but does not model delay.

`FraudLabel.LEGITIMATE = 0` and `FraudLabel.FRAUD = 1`. It is ground truth for offline
evaluation, never a transaction-time serving feature. Future UNKNOWN/PENDING labels can
be introduced through a new contract rather than weakening the binary source contract.

## Directory lifecycle and pipeline

```text
data/raw       untouched downloaded daily handbook .pkl batches
     -> data/interim  validated canonical Parquet plus manifest
     -> data/processed strict train/validation/test Parquet plus split manifests
```

All data files are ignored. A manifest contains no machine path and records dataset and
source versions, canonical schema version, checksum, counts, date range, source,
generation timestamp, and optional generator seed.

```powershell
uv run python scripts/data/download_or_generate_handbook.py --days 3
uv run python scripts/data/prepare_historical_data.py data/raw/fraud-handbook
uv run python scripts/data/split_historical_data.py data/interim/handbook.parquet `
  --train-end 2018-04-02T00:00:00Z --validation-end 2018-04-03T00:00:00Z
```

The default upstream revision is `main`; pin it to a commit with `--source-revision`
when publishing a reproducible benchmark result. The raw input checksum and manifest
should accompany any model artifact later. The downloader copies the public upstream
pickle batches unchanged.

## Validation and leakage policy

Preparation fails rather than drops rows when required columns, IDs, timestamps,
amounts, labels, customer IDs, merchant IDs, uniqueness, or temporal orderability are
invalid. Temporal partitions are strict: train `< train_end`, validation
`[train_end, validation_end)`, test `>= validation_end`, and the validator rejects empty
partitions, duplicate IDs, and timestamp overlap.

A feature for event time T may use only information available at or before T. Future
labels, final outcomes, and post-event aggregates are prohibited as scoring-time
features. No feature engineering occurs in Phase 2.

## Simulator

```text
seeded customer + merchant profiles
-> scenario engine
-> synthetic operational transactions
-> existing TransactionRequest API contract / JSONL file
```

Supported scenarios are NORMAL, CARD_TESTING, HIGH_VELOCITY, ACCOUNT_TAKEOVER,
IMPOSSIBLE_TRAVEL, NEW_DEVICE_HIGH_VALUE, SHARED_DEVICE_FRAUD, and FRAUD_RING.
They encode understandable timing, device, amount, location, and relationship patterns;
they do not model real identities, payment cards, or bank behavior. A `seed` owns all
random state, so identical configuration produces identical profiles and streams.

```powershell
uv run python -m fraudguard.simulation --seed 42 --transactions 20 `
  --scenario CARD_TESTING --output data/processed/demo-card-testing.jsonl
```

Direct API submission and Redpanda publication are not implemented in Phase 2.

## Current limits

The current source is simulated, has no label-delay model or currency/device/location
attributes, and is not a production fraud dataset. The simulator labels are scenario
annotations for demonstrations, not training data provenance. No model is trained,
registered, or promoted in this phase.
