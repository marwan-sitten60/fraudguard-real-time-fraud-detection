import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from fraudguard.core.config import Settings
from fraudguard.features.online.redis import RedisFeatureProvider, StoredFeatures
from fraudguard.persistence.postgres.connection import database_engine

pytestmark = pytest.mark.integration


def test_postgres_connectivity_schema_constraints():
    engine = database_engine(Settings())
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
            assert {"transactions", "fraud_decisions", "fraud_labels"} <= set(
                inspect(connection).get_table_names()
            )
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
            with pytest.raises(IntegrityError):
                connection.execute(
                    text("""INSERT INTO transactions
                    (transaction_id,user_id,merchant_id,device_id,timestamp,amount,currency,
                     merchant_category,payment_channel,country,ip_country)
                    VALUES (:id,'test','test','test',now(),-1,'USD','5411','ONLINE','US','US')"""),
                    {"id": f"test_{uuid4().hex}"},
                )
            connection.rollback()
    finally:
        engine.dispose()


def test_redis_roundtrip(transaction):
    async def run():
        settings = Settings()
        client = Redis(host=settings.redis_host, port=settings.redis_port, socket_timeout=2)
        provider = RedisFeatureProvider(client, 300)
        from dataclasses import replace

        unique = replace(transaction, user_id=f"test_{uuid4().hex}")
        key = f"fraudguard:features:example-v1:{unique.user_id}"
        try:
            assert await provider.ready()
            snapshot = StoredFeatures(
                version="example-v1", as_of=datetime.now(UTC), values={"x": 1}
            )
            await client.set(key, snapshot.model_dump_json(), ex=30)
            assert (await provider.get_features(unique)).values == {"x": 1}
        finally:
            await client.delete(key)
            await provider.close()

    asyncio.run(run())
