from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from recommendation.ports import (
    ResearchNotFoundError,
    ResearchScoreUnavailableError,
)
from recommendation.recommendation_adapter import build_impact_simulator
from recommendation.repository import RecommendationSetNotFoundError
from recommendation.simulation.repository import (
    RecommendationSimulationNotFoundError,
)
from recommendation.simulation.schemas import SimulationResult

router = APIRouter(tags=["recommendation-simulation"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/research/{research_id}/simulate",
    response_model=SimulationResult,
    status_code=status.HTTP_201_CREATED,
)
def simulate_impact(research_id: int, db: DbSession) -> SimulationResult:
    try:
        return build_impact_simulator(db).simulate(research_id)
    except ResearchNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (ResearchScoreUnavailableError, RecommendationSetNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.get(
    "/research/{research_id}/simulation",
    response_model=SimulationResult,
)
def get_simulation(research_id: int, db: DbSession) -> SimulationResult:
    try:
        return build_impact_simulator(db).get_latest(research_id)
    except (
        RecommendationSetNotFoundError,
        RecommendationSimulationNotFoundError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
