import asyncio
import logging
from math import isfinite
from time import perf_counter

from fraudguard.core.exceptions import FeatureUnavailable, ModelUnavailable
from fraudguard.domain.entities import FraudScore, Transaction
from fraudguard.domain.interfaces import DecisionPolicy, FeatureProvider, FraudModel, RuleEngine
from fraudguard.monitoring.metrics import Metrics

logger = logging.getLogger(__name__)


class ScoringService:
    def __init__(
        self,
        features: FeatureProvider,
        rules: RuleEngine,
        model: FraudModel,
        policy: DecisionPolicy,
        metrics: Metrics,
        feature_timeout_ms: int,
    ) -> None:
        self.features = features
        self.rules = rules
        self.model = model
        self.policy = policy
        self.metrics = metrics
        self.feature_timeout_seconds = feature_timeout_ms / 1000

    async def ready(self) -> bool:
        try:
            async with asyncio.timeout(self.feature_timeout_seconds):
                return self.model.ready and await self.features.ready()
        except Exception:
            return False

    async def score(self, transaction: Transaction) -> FraudScore:
        started = perf_counter()
        self.metrics.scoring_requests.inc()
        try:
            try:
                async with asyncio.timeout(self.feature_timeout_seconds):
                    features = await self.features.get_features(transaction)
            except Exception as exc:
                self.metrics.feature_errors.inc()
                raise FeatureUnavailable("online features unavailable") from exc
            rules = self.rules.evaluate(transaction, features)
            try:
                if not self.model.ready:
                    raise ModelUnavailable("model not ready")
                prediction = self.model.predict(transaction, features)
                if (
                    not isfinite(prediction.risk_score)
                    or not 0 <= prediction.risk_score <= 1
                    or prediction.model_version != self.model.version
                ):
                    raise ModelUnavailable("invalid model output")
            except Exception as exc:
                self.metrics.model_errors.inc()
                raise ModelUnavailable("model unavailable") from exc
            decision = self.policy.decide(prediction, rules)
            elapsed = (perf_counter() - started) * 1000
            score = FraudScore(
                transaction.transaction_id,
                prediction.risk_score,
                decision,
                rules.reason_codes,
                prediction.model_version,
                elapsed,
            )
            self.metrics.decisions.labels(decision=decision.value).inc()
            logger.info(
                "transaction_scored",
                extra={
                    "model_version": prediction.model_version,
                    "decision": decision.value,
                    "latency_ms": round(elapsed, 3),
                },
            )
            return score
        finally:
            self.metrics.scoring_duration.observe(perf_counter() - started)
