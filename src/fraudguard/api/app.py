from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from fraudguard import __version__
from fraudguard.api.middleware import RequestMiddleware
from fraudguard.api.routes import health, scoring
from fraudguard.core.config import Settings
from fraudguard.core.exceptions import ServingUnavailable
from fraudguard.core.logging import configure_logging, request_id_context
from fraudguard.decision.policy import ThresholdDecisionPolicy
from fraudguard.domain.interfaces import FeatureProvider
from fraudguard.features.online.mock import MockFeatureProvider
from fraudguard.features.online.redis import RedisFeatureProvider
from fraudguard.models.loader import load_model
from fraudguard.monitoring.metrics import Metrics
from fraudguard.rules.engine import BasicRuleEngine
from fraudguard.services.scoring_service import ScoringService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)
    metrics = Metrics(__version__)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        model = load_model(settings)
        features: FeatureProvider
        if settings.feature_backend == "redis":
            features = RedisFeatureProvider(
                Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    socket_timeout=settings.feature_timeout_ms / 1000,
                    socket_connect_timeout=settings.feature_timeout_ms / 1000,
                    decode_responses=True,
                ),
                settings.feature_max_age_seconds,
            )
        else:
            features = MockFeatureProvider()
        app.state.scoring_service = ScoringService(
            features,
            BasicRuleEngine(),
            model,
            ThresholdDecisionPolicy(
                settings.decision_review_threshold, settings.decision_block_threshold
            ),
            metrics,
            settings.feature_timeout_ms,
        )
        try:
            yield
        finally:
            await features.close()

    app = FastAPI(
        title="FraudGuard",
        version=__version__,
        lifespan=lifespan,
        description="Phase 1 foundation. Current Fraud Model = MOCK. No live fraud protection.",
    )
    app.state.metrics = metrics
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(
        RequestMiddleware, metrics=metrics, max_request_bytes=settings.max_request_bytes
    )

    @app.exception_handler(ServingUnavailable)
    async def unavailable(request: Request, exc: ServingUnavailable) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": "serving_unavailable", "request_id": request_id_context.get()},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic's default errors echo inputs, which could contain sensitive data.
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_transaction", "request_id": request_id_context.get()},
        )

    app.include_router(health.router)
    app.include_router(scoring.router)
    return app
