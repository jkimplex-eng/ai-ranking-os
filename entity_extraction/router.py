from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from entity_extraction import service
from entity_extraction.schemas import (
    ExtractionBatchInput,
    ExtractionInput,
    ExtractionResult,
)

router = APIRouter(prefix="/entity-extraction", tags=["entity-extraction"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/extract", response_model=ExtractionResult, status_code=status.HTTP_201_CREATED)
def extract_entities(payload: ExtractionInput, db: DbSession) -> ExtractionResult:
    try:
        return service.extract(db, payload)
    except service.DuplicateResponseError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post(
    "/batch",
    response_model=list[ExtractionResult],
    status_code=status.HTTP_201_CREATED,
)
def extract_entities_batch(
    payload: ExtractionBatchInput | list[ExtractionInput],
    db: DbSession,
) -> list[ExtractionResult]:
    items = payload if isinstance(payload, list) else payload.items
    try:
        return service.extract_batch(db, items)
    except service.DuplicateResponseError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/{response_id}", response_model=ExtractionResult)
def get_extraction(response_id: str, db: DbSession) -> ExtractionResult:
    try:
        return service.get_extraction(db, response_id)
    except service.ExtractionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

