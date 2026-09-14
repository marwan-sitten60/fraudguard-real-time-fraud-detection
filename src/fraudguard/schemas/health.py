from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy", "ready", "not_ready"]
    application_version: str
    model_version: str | None = None


class ErrorResponse(BaseModel):
    error: str
    request_id: str
