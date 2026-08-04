from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from query_intent import service
from query_intent.schemas import IntentBatchInput, IntentInput, IntentResult

router = APIRouter(prefix="/intent", tags=["query-intent"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/classify", response_model=IntentResult, status_code=status.HTTP_201_CREATED)
def classify_intent(payload: IntentInput, db: DbSession) -> IntentResult:
    try:
        return service.classify(db, payload)
    except service.DuplicateIntentRequestError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post(
    "/batch",
    response_model=list[IntentResult],
    status_code=status.HTTP_201_CREATED,
)
def classify_intent_batch(
    payload: IntentBatchInput | list[IntentInput],
    db: DbSession,
) -> list[IntentResult]:
    items = payload if isinstance(payload, list) else payload.items
    try:
        return service.classify_batch(db, items)
    except service.DuplicateIntentRequestError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/{request_id}", response_model=IntentResult)
def get_intent(request_id: str, db: DbSession) -> IntentResult:
    try:
        return service.get_result(db, request_id)
    except service.IntentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

