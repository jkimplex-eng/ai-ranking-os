from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from query_executor import service
from query_executor.schemas import (
    CancellationResult,
    ExecutionPlan,
    ExecutorResult,
)
from query_executor.streaming import stream_result

router = APIRouter(prefix="/executor", tags=["query-executor"])
DbSession = Annotated[Session, Depends(get_db)]


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, service.ExecutorNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.post("/run", response_model=ExecutorResult, status_code=status.HTTP_201_CREATED)
def run_plan(plan: ExecutionPlan, db: DbSession) -> ExecutorResult:
    try:
        return service.run(db, plan)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.post("/stream", response_class=StreamingResponse)
def stream_plan(plan: ExecutionPlan, db: DbSession) -> StreamingResponse:
    try:
        result = service.run(db, plan)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return StreamingResponse(stream_result(result), media_type="application/x-ndjson")


@router.post("/{execution_id}/cancel", response_model=CancellationResult)
def cancel_execution(execution_id: str, db: DbSession) -> CancellationResult:
    try:
        return service.cancel(db, execution_id)
    except (service.ExecutorNotFoundError, service.ExecutorConflictError) as error:
        raise _http_error(error) from error


@router.get("/{execution_id}", response_model=ExecutorResult)
def get_execution(execution_id: str, db: DbSession) -> ExecutorResult:
    try:
        return service.get_result(db, execution_id)
    except (service.ExecutorNotFoundError, service.ExecutorConflictError) as error:
        raise _http_error(error) from error
