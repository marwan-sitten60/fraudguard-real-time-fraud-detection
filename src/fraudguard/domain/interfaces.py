"""Technology-neutral serving and persistence ports; no framework dependencies."""

from typing import Protocol

from fraudguard.domain.entities import (
    FeatureSnapshot,
    FraudScore,
    Prediction,
    RuleResult,
    Transaction,
)
from fraudguard.domain.enums import Decision


class FeatureProvider(Protocol):
    async def get_features(self, transaction: Transaction) -> FeatureSnapshot: ...
    async def ready(self) -> bool: ...
    async def close(self) -> None: ...


class FraudModel(Protocol):
    @property
    def version(self) -> str: ...
    @property
    def ready(self) -> bool: ...
    def predict(self, transaction: Transaction, features: FeatureSnapshot) -> Prediction: ...


class RuleEngine(Protocol):
    def evaluate(self, transaction: Transaction, features: FeatureSnapshot) -> RuleResult: ...


class DecisionPolicy(Protocol):
    def decide(self, prediction: Prediction, rules: RuleResult) -> Decision: ...


class TransactionRepository(Protocol):
    """Future asynchronous consumer boundary, never called by scoring."""

    async def save_scored(self, transaction: Transaction, score: FraudScore) -> None: ...


class ModelRegistry(Protocol):
    """Resolve/download validated artifacts during deployment/startup only."""

    def resolve_artifact(self, name: str, alias: str) -> str: ...
