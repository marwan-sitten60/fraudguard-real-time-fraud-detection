"""Measure the Phase 4 Redis feature path without invoking a fraud model."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter

from redis.asyncio import Redis

from fraudguard.domain.entities import Transaction
from fraudguard.domain.enums import PaymentChannel
from fraudguard.features.online.contract import CUSTOMER_FEATURES, MERCHANT_FEATURES
from fraudguard.features.online.production_redis import (
    OnlineSnapshot,
    ProductionRedisFeatureProvider,
    assemble_online_features,
    customer_key,
    merchant_key,
)


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(quantile * len(ordered)))]


def summary(values: list[float]) -> dict[str, float]:
    return {
        "p50_ms": percentile(values, 0.50),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
    }


async def main(host: str, port: int, requests: int, concurrency: int) -> None:
    client = Redis(host=host, port=port, decode_responses=True, socket_timeout=2)
    provider = ProductionRedisFeatureProvider(client, 300)
    transaction = Transaction(
        "benchmark-transaction",
        "benchmark-customer",
        "benchmark-merchant",
        "benchmark-device",
        datetime.now(UTC),
        Decimal("42.50"),
        "USD",
        "5411",
        PaymentChannel.ONLINE,
        "US",
        "US",
    )
    now = datetime.now(UTC)
    customer = OnlineSnapshot(
        entity_id=transaction.user_id,
        updated_at=now,
        values={name: 10.0 for name in CUSTOMER_FEATURES},
    )
    merchant = OnlineSnapshot(
        entity_id=transaction.merchant_id,
        updated_at=now,
        values={name: 10.0 for name in MERCHANT_FEATURES},
    )
    keys = (customer_key(transaction.user_id), merchant_key(transaction.merchant_id))
    await client.set(keys[0], customer.model_dump_json(), ex=300)
    await client.set(keys[1], merchant.model_dump_json(), ex=300)
    semaphore = asyncio.Semaphore(concurrency)

    async def retrieve(assemble: bool) -> float:
        async with semaphore:
            started = perf_counter()
            snapshot = await provider.get_features(transaction)
            if assemble:
                assemble_online_features(transaction, snapshot)
            return (perf_counter() - started) * 1000

    await provider.get_features(transaction)
    retrieval = await asyncio.gather(*(retrieve(False) for _ in range(requests)))
    combined = await asyncio.gather(*(retrieve(True) for _ in range(requests)))
    snapshot = await provider.get_features(transaction)
    assembly: list[float] = []
    for _ in range(requests):
        started = perf_counter()
        assemble_online_features(transaction, snapshot)
        assembly.append((perf_counter() - started) * 1000)
    print(
        json.dumps(
            {
                "requests": requests,
                "concurrency": concurrency,
                "redis_commands_per_request": 2,
                "reads_are_concurrent": True,
                "retrieval": summary(retrieval),
                "assembly": summary(assembly),
                "combined": summary(combined),
            },
            indent=2,
        )
    )
    await client.delete(*keys)
    await provider.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port, args.requests, args.concurrency))
