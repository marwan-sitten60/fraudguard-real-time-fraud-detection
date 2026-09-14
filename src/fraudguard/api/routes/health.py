from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from fraudguard import __version__
from fraudguard.api.dependencies import get_scoring_service
from fraudguard.schemas.health import HealthResponse
from fraudguard.services.scoring_service import ScoringService

router = APIRouter(tags=["operations"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="healthy", application_version=__version__)


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
async def ready(
    response: Response,
    service: Annotated[ScoringService, Depends(get_scoring_service)],
) -> HealthResponse:
    available = await service.ready()
    response.status_code = 200 if available else 503
    return HealthResponse(
        status="ready" if available else "not_ready",
        application_version=__version__,
        model_version=service.model.version,
    )


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    return Response(
        content=generate_latest(request.app.state.metrics.registry),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )
