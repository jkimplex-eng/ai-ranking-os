from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from alert.ports import AlertDataUnavailableError
from alert.research_adapter import build_alert_engine
from alert.schemas import AlertRead
from backend.app.database import get_db

router = APIRouter(prefix="/entities", tags=["alert"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{entity_id}/alerts", response_model=list[AlertRead])
def get_alerts(entity_id: UUID, db: DbSession) -> list[AlertRead]:
    return build_alert_engine(db).history(entity_id)


@router.post(
    "/{entity_id}/alerts/evaluate",
    response_model=list[AlertRead],
    status_code=status.HTTP_201_CREATED,
)
def evaluate_alerts(entity_id: UUID, db: DbSession) -> list[AlertRead]:
    try:
        return build_alert_engine(db).evaluate(entity_id)
    except AlertDataUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

