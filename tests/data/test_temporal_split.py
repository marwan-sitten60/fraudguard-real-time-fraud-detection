from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from fraudguard.data.labels import FraudLabel
from fraudguard.data.schemas import HistoricalTransaction
from fraudguard.data.temporal_split import (
    TemporalSplitConfig,
    temporal_split,
)
from fraudguard.data.validation import DataValidationError


def rows() -> list[HistoricalTransaction]:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    return [
        HistoricalTransaction(
            transaction_id=f"tx_{index}",
            event_time=start + timedelta(days=index),
            customer_id="customer_1",
            merchant_id="merchant_1",
            amount=Decimal("1.00"),
            fraud_label=FraudLabel(index % 2),
            source="fixture",
        )
        for index in range(6)
    ]


def test_strict_temporal_split_has_no_overlap():
    data = rows()
    splits = temporal_split(
        data,
        TemporalSplitConfig(data[2].event_time, data[4].event_time),
    )
    assert [len(splits.train), len(splits.validation), len(splits.test)] == [2, 2, 2]
    assert max(row.event_time for row in splits.train) < min(
        row.event_time for row in splits.validation
    )
    assert max(row.event_time for row in splits.validation) < min(
        row.event_time for row in splits.test
    )


def test_temporal_split_rejects_empty_partition():
    data = rows()
    with pytest.raises(DataValidationError, match="non-empty"):
        temporal_split(data, TemporalSplitConfig(data[0].event_time, data[4].event_time))


def test_temporal_split_rejects_reused_ids():
    data = rows()
    data[5] = HistoricalTransaction(
        transaction_id=data[0].transaction_id,
        event_time=data[5].event_time,
        customer_id="customer_1",
        merchant_id="merchant_1",
        amount=Decimal("1"),
        fraud_label=FraudLabel.FRAUD,
        source="fixture",
    )
    with pytest.raises(DataValidationError, match="duplicate transaction_id"):
        temporal_split(data, TemporalSplitConfig(data[2].event_time, data[4].event_time))
