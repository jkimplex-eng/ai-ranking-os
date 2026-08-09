from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from provider_recommendation.research_adapter import SqlAlchemyResearchUsageSource
from provider_recommendation.schemas import ProviderRecommendationRead
from provider_recommendation.service import SmartProviderRecommendationService

router = APIRouter(tags=["provider-recommendations"])
DbSession = Annotated[Session, Depends(get_db)]


def service(db: Session) -> SmartProviderRecommendationService:
    return SmartProviderRecommendationService(db, SqlAlchemyResearchUsageSource(db))


@router.post(
    "/research/{research_id}/provider-recommendations",
    response_model=list[ProviderRecommendationRead],
    status_code=status.HTTP_201_CREATED,
)
def generate(research_id: int, db: DbSession) -> list[ProviderRecommendationRead]:
    return service(db).generate(research_id)


@router.get(
    "/research/{research_id}/provider-recommendations",
    response_model=list[ProviderRecommendationRead],
)
def list_recommendations(research_id: int, db: DbSession) -> list[ProviderRecommendationRead]:
    return service(db).list(research_id)
