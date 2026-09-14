import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from fraudguard.data.schemas import HistoricalTransaction
from fraudguard.data.validation import validate_historical_transactions


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_name: str
    dataset_version: str
    schema_version: str
    source: str
    source_version: str
    row_count: int
    fraud_count: int
    legitimate_count: int
    fraud_rate: float
    minimum_event_time: str
    maximum_event_time: str
    unique_customers: int
    unique_merchants: int
    content_sha256: str
    generated_at: str
    generator_seed: int | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


def rows_checksum(rows: list[HistoricalTransaction]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            f"{row.transaction_id}|{row.event_time.isoformat()}|{row.customer_id}|"
            f"{row.merchant_id}|{row.amount}|{int(row.fraud_label)}\n".encode()
        )
    return digest.hexdigest()


def build_manifest(
    rows: list[HistoricalTransaction],
    *,
    dataset_name: str,
    dataset_version: str,
    source_version: str = "unspecified",
    generator_seed: int | None = None,
) -> DatasetManifest:
    summary = validate_historical_transactions(rows)
    return DatasetManifest(
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        schema_version=rows[0].schema_version,
        source=rows[0].source,
        source_version=source_version,
        row_count=summary.row_count,
        fraud_count=summary.fraud_count,
        legitimate_count=summary.row_count - summary.fraud_count,
        fraud_rate=summary.fraud_count / summary.row_count,
        minimum_event_time=summary.minimum_event_time.isoformat(),
        maximum_event_time=summary.maximum_event_time.isoformat(),
        unique_customers=len({row.customer_id for row in rows}),
        unique_merchants=len({row.merchant_id for row in rows}),
        content_sha256=rows_checksum(rows),
        generated_at=datetime.now(UTC).isoformat(),
        generator_seed=generator_seed,
    )


def write_manifest(manifest: DatasetManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.to_json(), encoding="utf-8")
