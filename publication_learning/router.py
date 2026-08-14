from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from publication_learning.schemas import ExperimentRead, InfluenceEstimateRead, LearningSummary
from publication_learning.service import PublicationLearningService

router = APIRouter(prefix="/publication-learning", tags=["publication-learning"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/evaluate/{research_id}", response_model=list[ExperimentRead])
def evaluate_research(research_id: int, db: DbSession) -> list[ExperimentRead]:
    try:
        return PublicationLearningService(db).evaluate_followup(research_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/entity/{entity_id}", response_model=LearningSummary)
def entity_learning(entity_id: UUID, db: DbSession) -> LearningSummary:
    return PublicationLearningService(db).summary(entity_id)


@router.get("/influence", response_model=list[InfluenceEstimateRead])
def influence_estimates(
    db: DbSession,
    provider: str | None = None,
    metric: str | None = None,
    category: str | None = None,
    min_samples: int = Query(default=1, ge=1),
) -> list[InfluenceEstimateRead]:
    filters = {
        key: value
        for key, value in {"provider": provider, "metric": metric, "category": category}.items()
        if value
    }
    return [
        item
        for item in PublicationLearningService(db).repository.estimates(filters)
        if item.sample_size >= min_samples
    ]
