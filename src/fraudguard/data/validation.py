from dataclasses import dataclass
from datetime import datetime

from fraudguard.data.labels import FraudLabel
from fraudguard.data.schemas import HistoricalTransaction


class DataValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    row_count: int
    fraud_count: int
    minimum_event_time: datetime
    maximum_event_time: datetime


def validate_historical_transactions(rows: list[HistoricalTransaction]) -> ValidationSummary:
    if not rows:
        raise DataValidationError(["dataset contains no rows"])
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        prefix = f"row {index} ({row.transaction_id})"
        if row.transaction_id in seen_ids:
            errors.append(f"{prefix}: duplicate transaction_id")
        seen_ids.add(row.transaction_id)
        if not row.customer_id:
            errors.append(f"{prefix}: customer_id is empty")
        if not row.merchant_id:
            errors.append(f"{prefix}: merchant_id is empty")
        if row.amount < 0:
            errors.append(f"{prefix}: amount is negative")
        if row.fraud_label not in (FraudLabel.LEGITIMATE, FraudLabel.FRAUD):
            errors.append(f"{prefix}: fraud_label is outside binary contract")
        if row.event_time.tzinfo is None or row.event_time.utcoffset() is None:
            errors.append(f"{prefix}: event_time is not timezone-aware")
    if errors:
        raise DataValidationError(errors)
    times = [row.event_time for row in rows]
    return ValidationSummary(
        row_count=len(rows),
        fraud_count=sum(row.fraud_label is FraudLabel.FRAUD for row in rows),
        minimum_event_time=min(times),
        maximum_event_time=max(times),
    )
