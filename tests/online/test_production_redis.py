import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from prometheus_client import generate_latest

from fraudguard.core.exceptions import FeatureUnavailable
from fraudguard.features.online.contract import CUSTOMER_FEATURES, MERCHANT_FEATURES
from fraudguard.features.online.production_redis import (
    OnlineSnapshot,
    ProductionRedisFeatureProvider,
    assemble_online_features,
    customer_key,
    merchant_key,
)
from fraudguard.monitoring.metrics import Metrics


def snapshot(entity_id: str, names: tuple[str, ...], *, updated_at: datetime | None = None) -> str:
    return OnlineSnapshot(
        entity_id=entity_id,
        updated_at=updated_at or datetime.now(UTC),
        values={name: 1.0 for name in names},
    ).model_dump_json()


def client_with(customer: str | None, merchant: str | None) -> AsyncMock:
    client = AsyncMock()
    client.get.side_effect = [customer, merchant]
    return client


def test_key_design_assembly_and_metrics(transaction) -> None:
    assert customer_key("u") == "fraudguard:features:v1:customer:u"
    assert merchant_key("m") == "fraudguard:features:v1:merchant:m"
    metrics = Metrics("test")
    client = client_with(
        snapshot(transaction.user_id, CUSTOMER_FEATURES),
        snapshot(transaction.merchant_id, MERCHANT_FEATURES),
    )
    features = asyncio.run(
        ProductionRedisFeatureProvider(client, 300, metrics).get_features(transaction)
    )
    assert assemble_online_features(transaction, features)["amount"] == float(transaction.amount)
    exposition = generate_latest(metrics.registry).decode()
    assert "fraudguard_feature_fetch_duration_seconds_count 1.0" in exposition
    assert all(name not in exposition for name in ("transaction_id", "user_id", "device_id"))


@pytest.mark.parametrize("failure", [ConnectionError("down"), TimeoutError("timeout")])
def test_redis_transport_failure_is_controlled(transaction, failure: Exception) -> None:
    metrics = Metrics("test")
    client = AsyncMock()
    client.get.side_effect = failure
    with pytest.raises(FeatureUnavailable, match="store unavailable"):
        asyncio.run(ProductionRedisFeatureProvider(client, 300, metrics).get_features(transaction))
    assert metrics.feature_fetch_errors._value.get() == 1.0


@pytest.mark.parametrize(
    ("customer_present", "merchant_present"),
    [(False, True), (True, False)],
    ids=["missing-customer", "missing-merchant"],
)
def test_missing_entity_snapshot_fails_closed(
    transaction, customer_present: bool, merchant_present: bool
) -> None:
    customer = snapshot(transaction.user_id, CUSTOMER_FEATURES) if customer_present else None
    merchant = snapshot(transaction.merchant_id, MERCHANT_FEATURES) if merchant_present else None
    metrics = Metrics("test")
    with pytest.raises(FeatureUnavailable, match="snapshot missing"):
        asyncio.run(
            ProductionRedisFeatureProvider(
                client_with(customer, merchant), 300, metrics
            ).get_features(transaction)
        )
    assert metrics.feature_missing._value.get() == 1.0


def invalid_customer_payload(transaction, case: str) -> str:
    now = datetime.now(UTC)
    raw = json.loads(snapshot(transaction.user_id, CUSTOMER_FEATURES))
    if case == "malformed":
        return "{bad json"
    if case == "wrong-version":
        raw["feature_contract_version"] = "fraud-online-features-v0"
    elif case == "wrong-entity":
        raw["entity_id"] = "another-customer"
    elif case == "stale":
        raw["updated_at"] = (now - timedelta(minutes=10)).isoformat()
    elif case == "future":
        raw["updated_at"] = (now + timedelta(minutes=10)).isoformat()
    elif case == "missing-feature":
        del raw["values"][CUSTOMER_FEATURES[0]]
    return json.dumps(raw)


@pytest.mark.parametrize(
    "case", ["malformed", "wrong-version", "wrong-entity", "stale", "future", "missing-feature"]
)
def test_invalid_snapshot_fails_closed(transaction, case: str) -> None:
    metrics = Metrics("test")
    with pytest.raises(FeatureUnavailable):
        asyncio.run(
            ProductionRedisFeatureProvider(
                client_with(
                    invalid_customer_payload(transaction, case),
                    snapshot(transaction.merchant_id, MERCHANT_FEATURES),
                ),
                300,
                metrics,
            ).get_features(transaction)
        )
    if case in {"stale", "future"}:
        assert metrics.feature_snapshot_stale._value.get() == 1.0
    elif case == "missing-feature":
        assert metrics.feature_missing._value.get() == 1.0
    else:
        assert metrics.feature_fetch_errors._value.get() == 1.0
