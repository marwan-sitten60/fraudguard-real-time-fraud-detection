from decimal import Decimal
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from fraudguard.domain.entities import Transaction
from fraudguard.domain.enums import PaymentChannel

Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class TransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: Identifier
    user_id: Identifier
    merchant_id: Identifier
    device_id: Identifier
    timestamp: AwareDatetime
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    merchant_category: str = Field(pattern=r"^[0-9]{4}$")
    payment_channel: PaymentChannel
    country: str = Field(pattern=r"^[A-Z]{2}$")
    ip_country: str = Field(pattern=r"^[A-Z]{2}$")

    @field_validator("amount", mode="before")
    @classmethod
    def reject_float_money(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("send amount as a decimal string, e.g. '49.95'")
        return value

    def to_domain(self) -> Transaction:
        return Transaction(**self.model_dump())
