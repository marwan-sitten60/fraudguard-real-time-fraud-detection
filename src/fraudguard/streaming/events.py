from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from fraudguard.domain.enums import Decision
from fraudguard.schemas.scoring import ScoringResponse
from fraudguard.schemas.transaction import Identifier, TransactionRequest


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID = Field(default_factory=uuid4)
    event_version: Literal[1] = 1
    occurred_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: Identifier


class TransactionCreated(Envelope):
    event_type: Literal["transaction.created"] = "transaction.created"
    payload: TransactionRequest


class TransactionScored(Envelope):
    event_type: Literal["transaction.scored"] = "transaction.scored"
    payload: ScoringResponse


class ReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: Identifier
    analyst_id: Identifier
    decision: Decision


class TransactionReviewed(Envelope):
    event_type: Literal["transaction.reviewed"] = "transaction.reviewed"
    payload: ReviewPayload


class ConfirmedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: Identifier
    label_source: str = Field(min_length=1, max_length=64)


class FraudConfirmed(Envelope):
    event_type: Literal["fraud.confirmed"] = "fraud.confirmed"
    payload: ConfirmedPayload


FraudEvent = Annotated[
    TransactionCreated | TransactionScored | TransactionReviewed | FraudConfirmed,
    Field(discriminator="event_type"),
]
