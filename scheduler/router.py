from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from scheduler.engine import (
    InvalidCronExpressionError,
    ScheduleNotFoundError,
)
from scheduler.research_adapter import build_scheduler_engine
from scheduler.schemas import (
    ScheduleCreate,
    ScheduleExecutionRead,
    ScheduleRead,
    ScheduleUpdate,
)

router = APIRouter(prefix="/schedules", tags=["scheduler"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(payload: ScheduleCreate, db: DbSession) -> ScheduleRead:
    try:
        return build_scheduler_engine(db).create(payload)
    except InvalidCronExpressionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("", response_model=list[ScheduleRead])
def list_schedules(db: DbSession) -> list[ScheduleRead]:
    return build_scheduler_engine(db).list()


@router.patch("/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: int, payload: ScheduleUpdate, db: DbSession
) -> ScheduleRead:
    try:
        return build_scheduler_engine(db).update(schedule_id, payload)
    except ScheduleNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InvalidCronExpressionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: DbSession) -> Response:
    try:
        build_scheduler_engine(db).delete(schedule_id)
    except ScheduleNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/run", response_model=list[ScheduleExecutionRead])
def run_due_schedules(db: DbSession) -> list[ScheduleExecutionRead]:
    return build_scheduler_engine(db).run_due()
