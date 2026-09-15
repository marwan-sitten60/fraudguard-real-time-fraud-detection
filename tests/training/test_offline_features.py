from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fraudguard.data.labels import FraudLabel
from fraudguard.data.schemas import HistoricalTransaction
from fraudguard.features.offline.historical import build_point_in_time_features


def row(identifier: str, when: datetime, amount: str, label: FraudLabel) -> HistoricalTransaction:
    return HistoricalTransaction(
        identifier, when, "customer", "merchant", Decimal(amount), label, "test"
    )


def test_features_use_only_prior_rows_and_exclude_current_label() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    rows = [
        row("first", start, "10", FraudLabel.FRAUD),
        row("second", start + timedelta(minutes=1), "20", FraudLabel.LEGITIMATE),
    ]
    frame = build_point_in_time_features(rows)
    assert frame.loc[0, "merchant_prior_fraud_count"] == 0
    assert frame.loc[1, "merchant_prior_fraud_count"] == 1
    assert frame.loc[1, "customer_prior_avg_amount"] == 10.0
    assert "fraud_label" not in [name for name in frame.columns if name != "fraud_label"]
