"""Seed ONLY an illustrative dev snapshot; not feature engineering."""

import asyncio
from datetime import UTC, datetime

from redis.asyncio import Redis

from fraudguard.core.config import Settings
from fraudguard.features.online.redis import StoredFeatures


async def main() -> None:
    settings = Settings()
    client = Redis(host=settings.redis_host, port=settings.redis_port)
    try:
        snapshot = StoredFeatures(version="example-v1", as_of=datetime.now(UTC), values={})
        await client.set(
            "fraudguard:features:example-v1:user_123",
            snapshot.model_dump_json(),
            ex=settings.feature_max_age_seconds,
        )
        print("Seeded example-v1 snapshot for the smoke test user; expires automatically.")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
