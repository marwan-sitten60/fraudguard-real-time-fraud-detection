from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fraudguard.data.labels import FraudLabel

CANONICAL_SCHEMA_VERSION = "historical-transaction-v1"


@dataclass(frozen=True, slots=True)
class HistoricalTransaction:
    """Canonical historical row with source-supported business fields only.

    ``processing_time`` is recorded by pipeline metadata, not inferred per source row.
    ``label_available_time`` is intentionally optional: the handbook exposes labels in
    the dataset but does not model when a real investigation would confirm them.
    """

    transaction_id: str
    event_time: datetime
    customer_id: str
    merchant_id: str
    amount: Decimal
    fraud_label: FraudLabel
    source: str
    schema_version: str = CANONICAL_SCHEMA_VERSION
    label_available_time: datetime | None = None

    def __post_init__(self) -> None:
        if not self.transaction_id or not self.customer_id or not self.merchant_id:
            raise ValueError("transaction, customer, and merchant IDs must be non-empty")
        if self.event_time.tzinfo is None or self.event_time.utcoffset() is None:
            raise ValueError("event_time must be timezone-aware")
        if self.label_available_time is not None and (
            self.label_available_time.tzinfo is None
            or self.label_available_time.utcoffset() is None
        ):
            raise ValueError("label_available_time must be timezone-aware when supplied")
        if not self.amount.is_finite() or self.amount < 0:
            raise ValueError("amount must be finite and non-negative")
