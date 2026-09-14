from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from redis.asyncio import Redis

from fraudguard.core.exceptions import FeatureUnavailable
from fraudguard.domain.entities import FeatureSnapshot, Transaction


class StoredFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    version: str = Field(pattern=r"^example-v1$")
    as_of: AwareDatetime
    values: dict[str, float]


class RedisFeatureProvider:
    """Minimal JSON snapshot adapter, NOT a feature store or final feature contract."""

    def __init__(self, client: Redis, max_age_seconds: int) -> None:
        self.client = client
        self.max_age_seconds = max_age_seconds

    async def get_features(self, transaction: Transaction) -> FeatureSnapshot:
        raw = await self.client.get(f"fraudguard:features:example-v1:{transaction.user_id}")
        if raw is None:
            raise FeatureUnavailable("required snapshot missing")
        try:
            snapshot = StoredFeatures.model_validate_json(raw)
        except ValueError as exc:
            raise FeatureUnavailable("invalid snapshot") from exc
        age = (datetime.now(UTC) - snapshot.as_of).total_seconds()
        if not 0 <= age <= self.max_age_seconds:
            raise FeatureUnavailable("snapshot stale or future dated")
        return FeatureSnapshot(snapshot.values, snapshot.as_of, snapshot.version)

    async def ready(self) -> bool:
        return bool(await self.client.ping())

    async def close(self) -> None:
        await self.client.aclose()
