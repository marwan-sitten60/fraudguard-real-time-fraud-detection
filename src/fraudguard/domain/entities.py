from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fraudguard.domain.enums import Decision, PaymentChannel


@dataclass(frozen=True, slots=True)
class Transaction:
    transaction_id: str
    user_id: str
    merchant_id: str
    device_id: str
    timestamp: datetime
    amount: Decimal
    currency: str
    merchant_category: str
    payment_channel: PaymentChannel
    country: str
    ip_country: str

    def __post_init__(self) -> None:
        if not self.amount.is_finite() or self.amount <= 0:
            raise ValueError("amount must be finite and positive")
        if self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone aware")


@dataclass(frozen=True, slots=True)
class FeatureSnapshot:
    values: Mapping[str, float]
    as_of: datetime
    version: str


@dataclass(frozen=True, slots=True)
class RuleResult:
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Prediction:
    risk_score: float
    model_version: str


@dataclass(frozen=True, slots=True)
class FraudScore:
    transaction_id: str
    risk_score: float
    decision: Decision
    reason_codes: tuple[str, ...]
    model_version: str
    latency_ms: float
