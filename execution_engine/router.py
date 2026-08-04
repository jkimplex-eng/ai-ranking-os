from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from execution_engine import service
from execution_engine.schemas import ExecutionCancel, ExecutionRead, QueueTaskRead
from execution_engine.worker_manager import WorkerManager

router = APIRouter(tags=["execution-engine"])
DbSession = Annotated[Session, Depends(get_db)]
worker_manager = WorkerManager()


def _http_error(error: service.ExecutionEngineError) -> HTTPException:
    if isinstance(error, service.ExecutionNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.post("/execution/start", response_model=ExecutionRead, status_code=status.HTTP_201_CREATED)
def start_execution(db: DbSession) -> ExecutionRead:
    try:
        return service.start_next_execution(
            db,
            worker_manager,
            retry_base_seconds=get_settings().execution_retry_base_seconds,
        )
    except service.ExecutionEngineError as error:
        raise _http_error(error) from error


@router.post("/execution/cancel", response_model=ExecutionRead)
def cancel_execution(payload: ExecutionCancel, db: DbSession) -> ExecutionRead:
    try:
        return service.cancel_execution(db, payload.execution_id)
    except service.ExecutionEngineError as error:
        raise _http_error(error) from error


@router.get("/execution/history", response_model=list[ExecutionRead])
def execution_history(db: DbSession) -> list[ExecutionRead]:
    return service.list_history(db)


@router.get("/execution/{execution_id}", response_model=ExecutionRead)
def get_execution(execution_id: int, db: DbSession) -> ExecutionRead:
    try:
        return service.get_execution(db, execution_id)
    except service.ExecutionEngineError as error:
        raise _http_error(error) from error


@router.get("/queue", response_model=list[QueueTaskRead])
def get_queue(db: DbSession) -> list[QueueTaskRead]:
    return service.list_queue(db)

