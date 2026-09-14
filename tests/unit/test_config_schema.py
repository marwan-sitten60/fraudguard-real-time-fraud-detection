from decimal import Decimal

import pytest
from pydantic import ValidationError

from fraudguard.core.config import Settings
from fraudguard.schemas.transaction import TransactionRequest


@pytest.mark.parametrize(
    "overrides",
    [
        {"decision_review_threshold": 0.8, "decision_block_threshold": 0.5},
        {"decision_review_threshold": 0.5, "decision_block_threshold": 0.5},
        {"decision_block_threshold": 1.1},
        {"app_port": 0},
        {"redis_port": 70000},
        {"app_env": "production"},
        {"cors_origins": ["*"]},
        {"model_backend": "real"},
    ],
)
def test_invalid_settings(settings, overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)


def test_environment_configuration(settings, monkeypatch):
    monkeypatch.setenv("DECISION_REVIEW_THRESHOLD", "0.4")
    assert Settings(_env_file=None).decision_review_threshold == 0.4


def test_money_is_decimal(payload):
    assert TransactionRequest.model_validate(payload).to_domain().amount == Decimal("49.95")


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", -1),
        ("amount", "NaN"),
        ("amount", "Infinity"),
        ("amount", True),
        ("amount", 0.23),
        ("amount", "1.12345"),
        ("amount", "123456789012345.1234"),
        ("timestamp", "2026-01-01T00:00:00"),
        ("currency", "usd"),
        ("country", "USA"),
        ("transaction_id", "bad id"),
        ("merchant_category", "groceries"),
        ("payment_channel", "UNKNOWN"),
        ("extra", "field"),
    ],
)
def test_invalid_transaction(payload, field, value):
    payload[field] = value
    with pytest.raises(ValidationError):
        TransactionRequest.model_validate(payload)
