from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ai_visibility import service
from ai_visibility.schemas import (
    VisibilityBatchInput,
    VisibilityInput,
    VisibilityResult,
)
from backend.app.database import get_db

router = APIRouter(prefix="/visibility", tags=["ai-visibility"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/calculate", response_model=VisibilityResult, status_code=status.HTTP_201_CREATED)
def calculate_visibility(payload: VisibilityInput, db: DbSession) -> VisibilityResult:
    return service.calculate(db, payload)


@router.post(
    "/batch",
    response_model=list[VisibilityResult],
    status_code=status.HTTP_201_CREATED,
)
def calculate_visibility_batch(
    payload: VisibilityBatchInput | list[VisibilityInput],
    db: DbSession,
) -> list[VisibilityResult]:
    items = payload if isinstance(payload, list) else payload.items
    return service.calculate_batch(db, items)


@router.get("/{entity_id}", response_model=VisibilityResult)
def get_visibility(entity_id: str, db: DbSession) -> VisibilityResult:
    try:
        return service.get_latest(db, entity_id)
    except service.VisibilityNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

