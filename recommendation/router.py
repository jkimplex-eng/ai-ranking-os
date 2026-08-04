from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from recommendation.engine import RecommendationEngine
from recommendation.ports import (
    ResearchNotFoundError,
    ResearchScoreUnavailableError,
)
from recommendation.repository import RecommendationSetNotFoundError
from recommendation.research_adapter import SqlAlchemyResearchScoreAdapter
from recommendation.schemas import RecommendationSet

router = APIRouter(tags=["recommendations"])
DbSession = Annotated[Session, Depends(get_db)]


def _engine(db: Session) -> RecommendationEngine:
    return RecommendationEngine(db, SqlAlchemyResearchScoreAdapter(db))


@router.post(
    "/research/{research_id}/recommendations",
    response_model=RecommendationSet,
    status_code=status.HTTP_201_CREATED,
)
def generate_recommendations(
    research_id: int,
    db: DbSession,
) -> RecommendationSet:
    try:
        return _engine(db).generate(research_id)
    except ResearchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ResearchScoreUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.get(
    "/research/{research_id}/recommendations",
    response_model=RecommendationSet,
)
def get_recommendations(
    research_id: int,
    db: DbSession,
) -> RecommendationSet:
    try:
        return _engine(db).get_latest(research_id)
    except RecommendationSetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
