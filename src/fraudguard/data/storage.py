from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from fraudguard.data.labels import FraudLabel
from fraudguard.data.schemas import HistoricalTransaction

CANONICAL_ARROW_SCHEMA = pa.schema(
    [
        pa.field("transaction_id", pa.string()),
        pa.field("event_time", pa.timestamp("us", tz="UTC")),
        pa.field("customer_id", pa.string()),
        pa.field("merchant_id", pa.string()),
        # Decimal strings preserve source money representation independent of float behavior.
        pa.field("amount", pa.string()),
        pa.field("fraud_label", pa.int8()),
        pa.field("source", pa.string()),
        pa.field("schema_version", pa.string()),
        pa.field("label_available_time", pa.timestamp("us", tz="UTC")),
    ]
)


def write_canonical_parquet(rows: list[HistoricalTransaction], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(
        [
            {
                "transaction_id": row.transaction_id,
                "event_time": row.event_time,
                "customer_id": row.customer_id,
                "merchant_id": row.merchant_id,
                "amount": str(row.amount),
                "fraud_label": int(row.fraud_label),
                "source": row.source,
                "schema_version": row.schema_version,
                "label_available_time": row.label_available_time,
            }
            for row in rows
        ],
        schema=CANONICAL_ARROW_SCHEMA,
    )
    pq.write_table(table, path, compression="zstd")


def read_canonical_parquet(path: Path) -> list[HistoricalTransaction]:
    table = pq.read_table(path, schema=CANONICAL_ARROW_SCHEMA)
    rows: list[HistoricalTransaction] = []
    for row in table.to_pylist():
        event_time = row["event_time"]
        if not isinstance(event_time, datetime):
            raise ValueError("event_time missing from canonical parquet")
        rows.append(
            HistoricalTransaction(
                transaction_id=str(row["transaction_id"]),
                event_time=event_time,
                customer_id=str(row["customer_id"]),
                merchant_id=str(row["merchant_id"]),
                amount=Decimal(str(row["amount"])),
                fraud_label=FraudLabel(int(row["fraud_label"])),
                source=str(row["source"]),
                schema_version=str(row["schema_version"]),
                label_available_time=row["label_available_time"],
            )
        )
    return rows
