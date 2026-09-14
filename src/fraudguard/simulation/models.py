from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fraudguard.data.labels import FraudLabel
from fraudguard.schemas.transaction import TransactionRequest


@dataclass(frozen=True, slots=True)
class CustomerProfile:
    customer_id: str
    home_country: str
    typical_amount_min: Decimal
    typical_amount_max: Decimal
    usual_merchant_categories: tuple[str, ...]
    usual_active_hours: tuple[int, int]
    known_device_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MerchantProfile:
    merchant_id: str
    merchant_category: str
    country: str
    typical_amount_min: Decimal
    typical_amount_max: Decimal
    base_risk_level: Decimal


@dataclass(frozen=True, slots=True)
class SimulatedTransaction:
    request: TransactionRequest
    fraud_label: FraudLabel
    scenario: str
    event_time: datetime
