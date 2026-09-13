from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from eis.repository import EISRepository
from eis.schemas import (
    EISBatchRequest,
    EISBatchResult,
    EISCalculateRequest,
    EISPriorityItem,
    EISRead,
)
from eis.service import METHODOLOGY_VERSION, EISService
from frozen_prompts.repository import FrozenPromptRepository
from geo_platforms.repository import PlatformRepository
from geo_platforms.service import PlatformNotFoundError

router = APIRouter(prefix="/api/v1/eis", tags=["eis"])
DbSession = Annotated[Session, Depends(get_db)]


def service(db: Session) -> EISService:
    return EISService(EISRepository(db), PlatformRepository(db), FrozenPromptRepository(db))


@router.post("/calculate", response_model=EISRead, status_code=status.HTTP_201_CREATED)
def calculate_eis(payload: EISCalculateRequest, db: DbSession) -> EISRead:
    try:
        return service(db).calculate(payload)
    except (PlatformNotFoundError, LookupError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/batch-prioritize", response_model=EISBatchResult)
def batch_prioritize(payload: EISBatchRequest, db: DbSession) -> EISBatchResult:
    try:
        items = service(db).prioritize(payload)
        return EISBatchResult(
            items=[
                EISPriorityItem(score=score, cost_efficiency=efficiency)
                for score, efficiency in items
            ],
            methodology_version=METHODOLOGY_VERSION,
            limitations=["Correlation-based estimates; no causal effect is claimed."],
        )
    except (PlatformNotFoundError, LookupError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{score_id}", response_model=EISRead)
def get_eis(score_id: UUID, db: DbSession) -> EISRead:
    item = EISRepository(db).get(score_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"EIS score {score_id} not found")
    return item


@router.get("/history/{platform_id}", response_model=list[EISRead])
def eis_history(
    platform_id: UUID, db: DbSession, limit: int = Query(default=100, ge=1, le=500)
) -> list[EISRead]:
    return EISRepository(db).history(platform_id, limit)
