import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fraudguard.data.labels import FraudLabel
from fraudguard.data.schemas import HistoricalTransaction
from fraudguard.domain.entities import Transaction
from fraudguard.domain.enums import PaymentChannel
from fraudguard.features.offline.historical import build_point_in_time_features
from fraudguard.features.online.backfill import snapshots_before
from fraudguard.features.online.production_redis import (
    ProductionRedisFeatureProvider,
    assemble_online_features,
    customer_key,
    merchant_key,
)


class MemoryRedis:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    async def get(self, key: str):
        return self.values.get(key)

    async def ping(self):
        return True

    async def aclose(self):
        return None


def historical_rows() -> list[HistoricalTransaction]:
    start = datetime.now(UTC) - timedelta(minutes=4)
    return [
        HistoricalTransaction(
            transaction_id=f"tx-{index:03}",
            event_time=start + timedelta(seconds=index * 4),
            customer_id=f"customer-{index % 5}",
            merchant_id=f"merchant-{(index * 3) % 4}",
            amount=Decimal(str(10 + (index * 7) % 91)),
            fraud_label=FraudLabel.LEGITIMATE,
            source="parity-fixture",
        )
        for index in range(55)
    ]


def test_backfill_online_offline_parity_for_30_representative_rows() -> None:
    rows = historical_rows()
    offline = build_point_in_time_features(rows).set_index("transaction_id")
    mapping = {
        "customer_prior_transaction_count": "customer_prior_count",
        "customer_prior_average_amount": "customer_prior_avg_amount",
        "customer_prior_std_amount": "customer_prior_std_amount",
        "customer_prior_max_amount": "customer_prior_max_amount",
        "seconds_since_previous_transaction": "seconds_since_customer_prior_tx",
        "merchant_prior_transaction_count": "merchant_prior_count",
        "merchant_prior_average_amount": "merchant_prior_avg_amount",
        "amount": "amount",
        "hour_of_day": "hour_of_day",
        "day_of_week": "day_of_week",
        "weekend_indicator": "is_weekend",
        "amount_to_customer_prior_average": "amount_to_customer_prior_avg",
    }
    mismatches: list[tuple[str, str, float]] = []
    maximum_difference = 0.0
    # Covers five customers, four merchants, varied event times, and increasingly warm history.
    for target in rows[25:55]:
        customers, merchants = snapshots_before(rows, target.event_time)
        client = MemoryRedis(
            {
                customer_key(target.customer_id): customers[target.customer_id].model_dump_json(),
                merchant_key(target.merchant_id): merchants[target.merchant_id].model_dump_json(),
            }
        )
        transaction = Transaction(
            target.transaction_id,
            target.customer_id,
            target.merchant_id,
            "device",
            target.event_time,
            target.amount,
            "USD",
            "5411",
            PaymentChannel.ONLINE,
            "US",
            "US",
        )
        history = asyncio.run(ProductionRedisFeatureProvider(client, 300).get_features(transaction))
        actual = assemble_online_features(transaction, history)
        expected = offline.loc[target.transaction_id]
        for online_name, offline_name in mapping.items():
            difference = abs(float(actual[online_name]) - float(expected[offline_name]))
            maximum_difference = max(maximum_difference, difference)
            if difference > 1e-12:
                mismatches.append((target.transaction_id, online_name, difference))
    assert mismatches == []
    assert maximum_difference <= 1e-12
