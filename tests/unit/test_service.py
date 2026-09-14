import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from fraudguard.core.exceptions import FeatureUnavailable, ModelUnavailable
from fraudguard.decision.policy import ThresholdDecisionPolicy
from fraudguard.domain.entities import Prediction
from fraudguard.features.online.mock import MockFeatureProvider
from fraudguard.models.predictor import MockFraudModel
from fraudguard.monitoring.metrics import Metrics
from fraudguard.rules.engine import BasicRuleEngine
from fraudguard.services.scoring_service import ScoringService


def service(features=None, model=None):
    return ScoringService(
        features or MockFeatureProvider(),
        BasicRuleEngine(),
        model or MockFraudModel(),
        ThresholdDecisionPolicy(0.5, 0.8),
        Metrics("test"),
        10,
    )


def test_success(transaction):
    app = service()
    score = asyncio.run(app.score(transaction))
    assert score.risk_score == 0.23 and score.latency_ms >= 0
    assert asyncio.run(app.ready())
    assert app.metrics.registry.get_sample_value("fraudguard_scoring_requests_total") == 1


def test_feature_failure(transaction):
    features = MockFeatureProvider()
    features.get_features = AsyncMock(side_effect=ConnectionError("secret"))
    app = service(features=features)
    with pytest.raises(FeatureUnavailable):
        asyncio.run(app.score(transaction))
    assert app.metrics.registry.get_sample_value("fraudguard_feature_errors_total") == 1


def test_feature_timeout(transaction):
    class Slow(MockFeatureProvider):
        async def get_features(self, transaction):
            await asyncio.sleep(0.1)
            return await super().get_features(transaction)

    with pytest.raises(FeatureUnavailable):
        asyncio.run(service(features=Slow()).score(transaction))


@pytest.mark.parametrize("failure", ["not_ready", "exception", "nan", "version"])
def test_model_failures(transaction, failure):
    model = MockFraudModel()
    if failure == "not_ready":
        model.ready = False
    elif failure == "exception":
        model.predict = Mock(side_effect=RuntimeError("secret"))
    else:
        model.predict = Mock(
            return_value=Prediction(
                float("nan") if failure == "nan" else 0.5,
                "other" if failure == "version" else "mock-v1",
            )
        )
    app = service(model=model)
    with pytest.raises(ModelUnavailable):
        asyncio.run(app.score(transaction))
    assert app.metrics.registry.get_sample_value("fraudguard_model_errors_total") == 1


def test_readiness_failure():
    features = MockFeatureProvider()
    features.ready = AsyncMock(side_effect=ConnectionError())
    assert not asyncio.run(service(features=features).ready())


def test_execution_order(transaction):
    order = []
    app = service()
    for obj, method, name in [(app.features, "get_features", "features")]:
        original = getattr(obj, method)

        async def wrapped(transaction, original=original, name=name):
            order.append(name)
            return await original(transaction)

        setattr(obj, method, wrapped)

    class Rules(BasicRuleEngine):
        def evaluate(self, *args):
            order.append("rules")
            return super().evaluate(*args)

    class Model(MockFraudModel):
        def predict(self, *args):
            order.append("model")
            return super().predict(*args)

    class Policy:
        def decide(self, prediction, rules):
            order.append("decision")
            return ThresholdDecisionPolicy(0.5, 0.8).decide(prediction, rules)

    app.rules, app.model, app.policy = Rules(), Model(), Policy()
    asyncio.run(app.score(transaction))
    assert order == ["features", "rules", "model", "decision"]
