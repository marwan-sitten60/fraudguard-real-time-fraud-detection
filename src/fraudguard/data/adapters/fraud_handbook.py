from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, tzinfo
from decimal import Decimal, InvalidOperation

from fraudguard.data.labels import FraudLabel
from fraudguard.data.schemas import HistoricalTransaction

HANDBOOK_SOURCE = "fraud-detection-handbook/simulated-data-raw"
REQUIRED_HANDBOOK_COLUMNS = frozenset(
    {"TRANSACTION_ID", "TX_DATETIME", "CUSTOMER_ID", "TERMINAL_ID", "TX_AMOUNT", "TX_FRAUD"}
)


class HandbookSchemaError(ValueError):
    pass


def validate_handbook_columns(columns: Sequence[str]) -> None:
    missing = sorted(REQUIRED_HANDBOOK_COLUMNS - set(columns))
    if missing:
        raise HandbookSchemaError(f"missing required handbook columns: {', '.join(missing)}")


def handbook_row_to_canonical(
    row: Mapping[str, object], *, source_timezone: tzinfo = UTC
) -> HistoricalTransaction:
    """Map documented columns only; extension columns are deliberately not inferred."""
    try:
        raw_time = datetime.fromisoformat(str(row["TX_DATETIME"]).replace("Z", "+00:00"))
        event_time = (
            raw_time.replace(tzinfo=source_timezone) if raw_time.tzinfo is None else raw_time
        )
        amount = Decimal(str(row["TX_AMOUNT"]))
        label = FraudLabel(int(str(row["TX_FRAUD"])))
        return HistoricalTransaction(
            transaction_id=f"handbook_{row['TRANSACTION_ID']}",
            event_time=event_time.astimezone(UTC),
            customer_id=f"customer_{row['CUSTOMER_ID']}",
            merchant_id=f"terminal_{row['TERMINAL_ID']}",
            amount=amount,
            fraud_label=label,
            source=HANDBOOK_SOURCE,
        )
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise HandbookSchemaError(f"invalid handbook row: {exc}") from exc
