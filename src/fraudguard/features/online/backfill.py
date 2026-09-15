"""Deterministic label-free historical state replay for Redis snapshots."""

from datetime import datetime

from redis.asyncio import Redis

from fraudguard.data.schemas import HistoricalTransaction
from fraudguard.features.online.contract import CUSTOMER_FEATURES, MERCHANT_FEATURES
from fraudguard.features.online.production_redis import OnlineSnapshot, customer_key, merchant_key


class _State:
    def __init__(self) -> None:
        self.count = 0
        self.total = 0.0
        self.total_squares = 0.0
        self.maximum = 0.0
        self.previous: datetime | None = None

    def values(self, names: tuple[str, ...], now: datetime) -> dict[str, float]:
        average = self.total / self.count if self.count else 0.0
        variance = max(0.0, self.total_squares / self.count - average**2) if self.count > 1 else 0.0
        raw = {
            "customer_prior_transaction_count": float(self.count),
            "customer_prior_average_amount": average,
            "customer_prior_std_amount": variance**0.5,
            "customer_prior_max_amount": self.maximum,
            "seconds_since_previous_transaction": 0.0
            if self.previous is None
            else (now - self.previous).total_seconds(),
            "merchant_prior_transaction_count": float(self.count),
            "merchant_prior_average_amount": average,
        }
        return {name: raw[name] for name in names}

    def update(self, row: HistoricalTransaction) -> None:
        amount = float(row.amount)
        self.count += 1
        self.total += amount
        self.total_squares += amount * amount
        self.maximum = max(self.maximum, amount)
        self.previous = row.event_time


def snapshots_before(
    rows: list[HistoricalTransaction], cutoff: datetime
) -> tuple[dict[str, OnlineSnapshot], dict[str, OnlineSnapshot]]:
    customers: dict[str, _State] = {}
    merchants: dict[str, _State] = {}
    for row in sorted(rows, key=lambda item: (item.event_time, item.transaction_id)):
        if row.event_time >= cutoff:
            break
        customers.setdefault(row.customer_id, _State()).update(row)
        merchants.setdefault(row.merchant_id, _State()).update(row)
    customer_payloads = {
        entity: OnlineSnapshot(
            entity_id=entity, updated_at=cutoff, values=state.values(CUSTOMER_FEATURES, cutoff)
        )
        for entity, state in customers.items()
    }
    merchant_payloads = {
        entity: OnlineSnapshot(
            entity_id=entity, updated_at=cutoff, values=state.values(MERCHANT_FEATURES, cutoff)
        )
        for entity, state in merchants.items()
    }
    return customer_payloads, merchant_payloads


async def backfill_redis(
    client: Redis, rows: list[HistoricalTransaction], cutoff: datetime, ttl_seconds: int
) -> int:
    customers, merchants = snapshots_before(rows, cutoff)
    pipeline = client.pipeline(transaction=False)
    for entity, payload in customers.items():
        pipeline.set(customer_key(entity), payload.model_dump_json(), ex=ttl_seconds)
    for entity, payload in merchants.items():
        pipeline.set(merchant_key(entity), payload.model_dump_json(), ex=ttl_seconds)
    await pipeline.execute()
    return len(customers) + len(merchants)
