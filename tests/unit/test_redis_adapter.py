import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from fraudguard.core.exceptions import FeatureUnavailable
from fraudguard.features.online.redis import RedisFeatureProvider, StoredFeatures


@pytest.mark.parametrize("kind", ["missing", "invalid", "stale", "future", "wrong_version", "nan"])
def test_rejects_unusable_snapshot(transaction, kind):
    raw = None
    if kind == "invalid":
        raw = "not-json"
    elif kind in {"stale", "future"}:
        delta = -301 if kind == "stale" else 30
        raw = StoredFeatures(
            version="example-v1", as_of=datetime.now(UTC) + timedelta(seconds=delta), values={}
        ).model_dump_json()
    elif kind == "wrong_version":
        raw = '{"version":"other", "as_of":"2026-01-01T00:00:00Z", "values":{}}'
    elif kind == "nan":
        raw = '{"version":"example-v1", "as_of":"2026-01-01T00:00:00Z", "values":{"x":NaN}}'
    client = AsyncMock()
    client.get.return_value = raw
    with pytest.raises(FeatureUnavailable):
        asyncio.run(RedisFeatureProvider(client, 300).get_features(transaction))


def test_snapshot_and_lifecycle(transaction):
    client = AsyncMock()
    client.get.return_value = StoredFeatures(
        version="example-v1", as_of=datetime.now(UTC), values={"example": 1}
    ).model_dump_json()
    provider = RedisFeatureProvider(client, 300)
    assert asyncio.run(provider.get_features(transaction)).values == {"example": 1}
    assert asyncio.run(provider.ready())
    asyncio.run(provider.close())
    client.aclose.assert_awaited_once()
