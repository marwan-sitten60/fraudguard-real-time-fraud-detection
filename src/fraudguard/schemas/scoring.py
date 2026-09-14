from pydantic import BaseModel, ConfigDict, Field

from fraudguard.domain.enums import Decision


class ScoringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: str
    risk_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    decision: Decision
    reason_codes: tuple[str, ...]
    model_version: str
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
