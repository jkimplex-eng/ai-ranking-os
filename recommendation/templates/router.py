from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from recommendation.repository import RecommendationSetNotFoundError
from recommendation.templates.repository import (
    RecommendationTemplateNotFoundError,
    RecommendationTemplateRepository,
)
from recommendation.templates.schemas import (
    ActionPlan,
    RecommendationTemplateRead,
)
from recommendation.templates.service import ActionPlanService

router = APIRouter(tags=["recommendation-templates"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/recommendation/templates",
    response_model=list[RecommendationTemplateRead],
)
def list_templates(db: DbSession) -> list[RecommendationTemplateRead]:
    return RecommendationTemplateRepository(db).list()


@router.get(
    "/recommendation/templates/{code}",
    response_model=RecommendationTemplateRead,
)
def get_template(code: str, db: DbSession) -> RecommendationTemplateRead:
    try:
        return RecommendationTemplateRepository(db).get_latest(code)
    except RecommendationTemplateNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get(
    "/research/{research_id}/action-plan",
    response_model=ActionPlan,
)
def get_action_plan(research_id: int, db: DbSession) -> ActionPlan:
    try:
        return ActionPlanService(db).get(research_id)
    except RecommendationSetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
