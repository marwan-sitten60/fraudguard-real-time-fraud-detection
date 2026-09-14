from datetime import UTC, datetime

from fraudguard.domain.entities import FeatureSnapshot, Transaction


class MockFeatureProvider:
    """Empty feature snapshot; no real historical features are available yet."""

    async def get_features(self, transaction: Transaction) -> FeatureSnapshot:
        return FeatureSnapshot(values={}, as_of=datetime.now(UTC), version="mock-v1")

    async def ready(self) -> bool:
        return True

    async def close(self) -> None:
        return None
