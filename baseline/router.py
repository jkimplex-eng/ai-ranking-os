from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from baseline.adapter import build_baseline_engine
from baseline.engine import BaselineDataUnavailableError, BaselineNotFoundError
from baseline.schemas import BaselineCreate, BaselineRead, EvaluationResult

router = APIRouter(prefix="/entities", tags=["baseline"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/{entity_id}/baseline",
    response_model=BaselineRead,
    status_code=status.HTTP_201_CREATED,
)
def set_baseline(
    entity_id: UUID, payload: BaselineCreate, db: DbSession
) -> BaselineRead:
    try:
        return build_baseline_engine(db).set(entity_id, payload)
    except BaselineDataUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{entity_id}/baseline", response_model=BaselineRead)
def get_baseline(entity_id: UUID, db: DbSession) -> BaselineRead:
    try:
        return build_baseline_engine(db).get(entity_id)
    except BaselineNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{entity_id}/baseline/evaluate", response_model=EvaluationResult)
def evaluate_baseline(entity_id: UUID, db: DbSession) -> EvaluationResult:
    try:
        return build_baseline_engine(db).evaluate(entity_id)
    except BaselineNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except BaselineDataUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

