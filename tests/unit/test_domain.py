import asyncio
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest

from fraudguard.decision.policy import ThresholdDecisionPolicy
from fraudguard.domain.entities import Prediction, RuleResult
from fraudguard.domain.enums import Decision
from fraudguard.features.online.mock import MockFeatureProvider
from fraudguard.models.predictor import MockFraudModel
from fraudguard.rules.engine import BasicRuleEngine


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, Decision.APPROVE),
        (0.4999, Decision.APPROVE),
        (0.5, Decision.REVIEW),
        (0.7999, Decision.REVIEW),
        (0.8, Decision.BLOCK),
        (1, Decision.BLOCK),
    ],
)
def test_threshold_boundaries(score, expected):
    assert (
        ThresholdDecisionPolicy(0.5, 0.8).decide(Prediction(score, "mock-v1"), RuleResult())
        == expected
    )


@pytest.mark.parametrize("score", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_prediction(score):
    with pytest.raises(ValueError):
        ThresholdDecisionPolicy(0.5, 0.8).decide(Prediction(score, "mock-v1"), RuleResult())


def test_policy_configuration():
    with pytest.raises(ValueError):
        ThresholdDecisionPolicy(0.8, 0.5)


def test_mock_and_rule(transaction):
    features = asyncio.run(MockFeatureProvider().get_features(transaction))
    assert MockFraudModel().predict(transaction, features) == Prediction(0.23, "mock-v1")
    assert BasicRuleEngine().evaluate(transaction, features).reason_codes == ()
    assert BasicRuleEngine().evaluate(
        replace(transaction, ip_country="EG"), features
    ).reason_codes == ("COUNTRY_MISMATCH",)


def test_domain_invariants(transaction):
    with pytest.raises(ValueError):
        replace(transaction, amount=Decimal("-1"))
    with pytest.raises(ValueError):
        replace(transaction, timestamp=datetime(2026, 1, 1))
