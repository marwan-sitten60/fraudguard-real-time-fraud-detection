from datetime import UTC
from decimal import Decimal

import pytest

from fraudguard.data.adapters.fraud_handbook import HandbookSchemaError, handbook_row_to_canonical
from fraudguard.data.manifest import build_manifest
from fraudguard.data.pipeline import load_handbook_rows, prepare_historical_dataset
from fraudguard.data.storage import read_canonical_parquet
from fraudguard.data.validation import DataValidationError, validate_historical_transactions


def source_row(transaction_id: int = 1, timestamp: str = "2018-04-01T00:00:00") -> dict[str, str]:
    return {
        "TRANSACTION_ID": str(transaction_id),
        "TX_DATETIME": timestamp,
        "CUSTOMER_ID": "100",
        "TERMINAL_ID": "200",
        "TX_AMOUNT": "12.34",
        "TX_FRAUD": "0",
    }


def write_source(path, rows: list[dict[str, str]]) -> None:
    columns = list(source_row().keys())
    lines = [",".join(columns)]
    lines.extend(",".join(row[column] for column in columns) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_adapter_uses_documented_fields_and_utc_assumption():
    row = handbook_row_to_canonical(source_row())
    assert row.transaction_id == "handbook_1"
    assert row.customer_id == "customer_100"
    assert row.merchant_id == "terminal_200"
    assert row.amount == Decimal("12.34")
    assert row.event_time.tzinfo is UTC
    assert row.label_available_time is None


@pytest.mark.parametrize(
    "field,value", [("TX_AMOUNT", "-1"), ("TX_FRAUD", "2"), ("TX_DATETIME", "bad")]
)
def test_adapter_rejects_invalid_source_rows(field, value):
    row = source_row()
    row[field] = value
    with pytest.raises(HandbookSchemaError):
        handbook_row_to_canonical(row)


def test_missing_source_column_fails(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("TRANSACTION_ID,TX_DATETIME\n1,2018-04-01T00:00:00\n", encoding="utf-8")
    with pytest.raises(HandbookSchemaError, match="missing required"):
        load_handbook_rows(source)


def test_pipeline_writes_canonical_parquet_and_manifest(tmp_path):
    source = tmp_path / "source.csv"
    write_source(source, [source_row(1), source_row(2, "2018-04-02T00:00:00")])
    parquet = tmp_path / "interim.parquet"
    manifest = prepare_historical_dataset(
        source,
        interim_path=parquet,
        manifest_path=tmp_path / "manifest.json",
        dataset_version="test-v1",
        source_version="fixture",
    )
    assert manifest.row_count == 2
    assert manifest.fraud_count == 0
    assert manifest.source_version == "fixture"
    assert len(read_canonical_parquet(parquet)) == 2


def test_validation_rejects_duplicate_ids():
    row = handbook_row_to_canonical(source_row())
    with pytest.raises(DataValidationError, match="duplicate transaction_id"):
        validate_historical_transactions([row, row])


def test_manifest_counts_and_checksum_are_deterministic():
    rows = [
        handbook_row_to_canonical(source_row(1)),
        handbook_row_to_canonical({**source_row(2), "TX_FRAUD": "1"}),
    ]
    first = build_manifest(rows, dataset_name="fixture", dataset_version="v1")
    second = build_manifest(rows, dataset_name="fixture", dataset_version="v1")
    assert first.fraud_count == 1 and first.legitimate_count == 1
    assert first.fraud_rate == 0.5 and first.content_sha256 == second.content_sha256
