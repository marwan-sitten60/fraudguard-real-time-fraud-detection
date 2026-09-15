from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    postgres_host: str = "127.0.0.1"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "fraudguard"
    postgres_user: str = "fraudguard"
    postgres_password: SecretStr = SecretStr("")
    redis_host: str = "127.0.0.1"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    mlflow_tracking_uri: str = "http://localhost:5000"
    model_name: str = "fraudguard"
    model_alias: str = "champion"
    model_backend: Literal["mock"] = "mock"
    feature_backend: Literal["mock", "redis", "redis_v1"] = "mock"
    feature_timeout_ms: int = Field(default=20, ge=1, le=1000)
    feature_max_age_seconds: int = Field(default=300, ge=1)
    decision_review_threshold: float = Field(default=0.5, ge=0, le=1)
    decision_block_threshold: float = Field(default=0.8, ge=0, le=1)
    max_request_bytes: int = Field(default=16384, ge=1024, le=1048576)
    cors_origins: list[str] = []

    @model_validator(mode="after")
    def validate_policy(self) -> "Settings":
        if self.decision_review_threshold >= self.decision_block_threshold:
            raise ValueError("review threshold must be below block threshold")
        if self.app_env == "production":
            raise ValueError("Phase 1 mock serving cannot be enabled in production")
        if "*" in self.cors_origins:
            raise ValueError("CORS origins must be explicit")
        return self
