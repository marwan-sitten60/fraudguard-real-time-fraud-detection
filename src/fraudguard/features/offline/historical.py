"""Point-in-time-correct stateful feature generation for canonical transactions."""

from dataclasses import dataclass
from datetime import datetime
from math import sqrt

import pandas as pd  # type: ignore[import-untyped]

from fraudguard.data.schemas import HistoricalTransaction
from fraudguard.features.offline.contract import FEATURE_NAMES


@dataclass(slots=True)
class _AmountState:
    count: int = 0
    total: float = 0.0
    total_squares: float = 0.0
    maximum: float = 0.0
    prior_time: datetime | None = None
    fraud_count: int = 0

    def mean(self) -> float:
        return self.total / self.count if self.count else 0.0

    def std(self) -> float:
        if self.count < 2:
            return 0.0
        variance = max(0.0, self.total_squares / self.count - self.mean() ** 2)
        return sqrt(variance)

    def update(self, amount: float, event_time: datetime, fraud_label: int) -> None:
        self.count += 1
        self.total += amount
        self.total_squares += amount * amount
        self.maximum = max(self.maximum, amount)
        self.prior_time = event_time
        self.fraud_count += fraud_label


def build_point_in_time_features(rows: list[HistoricalTransaction]) -> pd.DataFrame:
    """Build features without using a row's own or future data.

    Ties are deterministically ordered by transaction_id. Labels are treated as
    immediately available *after* prior transactions for this public benchmark;
    real label availability must replace this assumption before production use.
    """
    customers: dict[str, _AmountState] = {}
    merchants: dict[str, _AmountState] = {}
    output: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: (item.event_time, item.transaction_id)):
        amount = float(row.amount)
        customer = customers.setdefault(row.customer_id, _AmountState())
        merchant = merchants.setdefault(row.merchant_id, _AmountState())
        prior_mean = customer.mean()
        elapsed = (
            0.0
            if customer.prior_time is None
            else (row.event_time - customer.prior_time).total_seconds()
        )
        output.append(
            {
                "transaction_id": row.transaction_id,
                "event_time": row.event_time,
                "fraud_label": int(row.fraud_label),
                "amount": amount,
                "hour_of_day": row.event_time.hour,
                "day_of_week": row.event_time.weekday(),
                "is_weekend": int(row.event_time.weekday() >= 5),
                "customer_prior_count": customer.count,
                "customer_prior_avg_amount": prior_mean,
                "customer_prior_std_amount": customer.std(),
                "customer_prior_max_amount": customer.maximum,
                "amount_to_customer_prior_avg": amount / prior_mean if prior_mean else 0.0,
                "seconds_since_customer_prior_tx": elapsed,
                "merchant_prior_count": merchant.count,
                "merchant_prior_avg_amount": merchant.mean(),
                "merchant_prior_fraud_count": merchant.fraud_count,
                "merchant_prior_fraud_rate": merchant.fraud_count / merchant.count
                if merchant.count
                else 0.0,
            }
        )
        customer.update(amount, row.event_time, int(row.fraud_label))
        merchant.update(amount, row.event_time, int(row.fraud_label))
    frame = pd.DataFrame(output)
    return frame[["transaction_id", "event_time", "fraud_label", *FEATURE_NAMES]]
