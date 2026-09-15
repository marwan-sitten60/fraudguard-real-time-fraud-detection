"""Redis online snapshots for production-safe, label-free history features."""

import asyncio
from datetime import UTC, datetime
from time import perf_counter

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from redis.asyncio import Redis

from fraudguard.core.exceptions import FeatureUnavailable
from fraudguard.domain.entities import FeatureSnapshot, Transaction
from fraudguard.features.online.contract import (
    CUSTOMER_FEATURES,
    MERCHANT_FEATURES,
    ONLINE_FEATURE_CONTRACT_VERSION,
)
from fraudguard.monitoring.metrics import Metrics


class OnlineSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    feature_contract_version: str = Field(
        default=ONLINE_FEATURE_CONTRACT_VERSION, pattern=r"^fraud-online-features-v1$"
    )
    updated_at: AwareDatetime
    entity_id: str = Field(min_length=1)
    values: dict[str, float]


def customer_key(customer_id: str) -> str:
    return f"fraudguard:features:v1:customer:{customer_id}"


def merchant_key(merchant_id: str) -> str:
    return f"fraudguard:features:v1:merchant:{merchant_id}"


class ProductionRedisFeatureProvider:
    """Two-key snapshot fetch; absence, bad version, or stale data fails closed."""

    def __init__(self, client: Redis, max_age_seconds: int, metrics: Metrics | None = None) -> None:
        self.client, self.max_age_seconds = client, max_age_seconds
        self.metrics = metrics

    async def get_features(self, transaction: Transaction) -> FeatureSnapshot:
        started = perf_counter()
        try:
            try:
                customer_raw, merchant_raw = await asyncio.gather(
                    self.client.get(customer_key(transaction.user_id)),
                    self.client.get(merchant_key(transaction.merchant_id)),
                )
            except Exception as exc:
                if self.metrics is not None:
                    self.metrics.feature_fetch_errors.inc()
                raise FeatureUnavailable("online feature store unavailable") from exc
            customer = self._parse(customer_raw, transaction.user_id, CUSTOMER_FEATURES)
            merchant = self._parse(merchant_raw, transaction.merchant_id, MERCHANT_FEATURES)
            values = customer.values | merchant.values
            return FeatureSnapshot(
                values,
                min(customer.updated_at, merchant.updated_at),
                ONLINE_FEATURE_CONTRACT_VERSION,
            )
        finally:
            if self.metrics is not None:
                self.metrics.feature_fetch_duration.observe(perf_counter() - started)

    def _parse(
        self, raw: str | bytes | None, entity_id: str, required: tuple[str, ...]
    ) -> OnlineSnapshot:
        if raw is None:
            if self.metrics is not None:
                self.metrics.feature_missing.inc()
            raise FeatureUnavailable("required online feature snapshot missing")
        try:
            snapshot = OnlineSnapshot.model_validate_json(raw)
        except ValueError as exc:
            if self.metrics is not None:
                self.metrics.feature_fetch_errors.inc()
            raise FeatureUnavailable("invalid online feature snapshot") from exc
        age = (datetime.now(UTC) - snapshot.updated_at).total_seconds()
        if snapshot.entity_id != entity_id:
            if self.metrics is not None:
                self.metrics.feature_fetch_errors.inc()
            raise FeatureUnavailable("online feature snapshot entity mismatch")
        if not 0 <= age <= self.max_age_seconds:
            if self.metrics is not None:
                self.metrics.feature_snapshot_stale.inc()
            raise FeatureUnavailable("online feature snapshot stale or future-dated")
        if any(name not in snapshot.values for name in required):
            if self.metrics is not None:
                self.metrics.feature_missing.inc()
            raise FeatureUnavailable("online feature snapshot incomplete")
        return snapshot

    async def ready(self) -> bool:
        return bool(await self.client.ping())

    async def close(self) -> None:
        await self.client.aclose()


def assemble_online_features(
    transaction: Transaction, history: FeatureSnapshot
) -> dict[str, float]:
    values = dict(history.values)
    amount = float(transaction.amount)
    average = values["customer_prior_average_amount"]
    values.update(
        {
            "amount": amount,
            "hour_of_day": float(transaction.timestamp.hour),
            "day_of_week": float(transaction.timestamp.weekday()),
            "weekend_indicator": float(transaction.timestamp.weekday() >= 5),
            "amount_to_customer_prior_average": amount / average if average else 0.0,
        }
    )
    return values
