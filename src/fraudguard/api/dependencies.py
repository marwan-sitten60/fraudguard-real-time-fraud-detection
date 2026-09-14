from fastapi import Request

from fraudguard.services.scoring_service import ScoringService


def get_scoring_service(request: Request) -> ScoringService:
    service: ScoringService = request.app.state.scoring_service
    return service
