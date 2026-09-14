from typing import Annotated

from fastapi import APIRouter, Depends

from fraudguard.api.dependencies import get_scoring_service
from fraudguard.schemas.health import ErrorResponse
from fraudguard.schemas.scoring import ScoringResponse
from fraudguard.schemas.transaction import TransactionRequest
from fraudguard.services.scoring_service import ScoringService

router = APIRouter(prefix="/api/v1/transactions", tags=["scoring"])


@router.post(
    "/score",
    response_model=ScoringResponse,
    responses={
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def score_transaction(
    transaction: TransactionRequest,
    service: Annotated[ScoringService, Depends(get_scoring_service)],
) -> ScoringResponse:
    return ScoringResponse.model_validate(await service.score(transaction.to_domain()))
