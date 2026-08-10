from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from change_detection.dependencies import build_change_detection
from change_detection.schemas import ResearchChangeRead
from change_detection.service import ChangeNotFoundError

router = APIRouter(prefix="/research", tags=["change-detection"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/{research_id}/changes", response_model=ResearchChangeRead)
def detect_changes(research_id: int, db: DbSession) -> ResearchChangeRead:
    try:
        return build_change_detection(db).detect(research_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{research_id}/changes", response_model=ResearchChangeRead)
def get_changes(research_id: int, db: DbSession) -> ResearchChangeRead:
    try:
        return build_change_detection(db).get(research_id)
    except ChangeNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
