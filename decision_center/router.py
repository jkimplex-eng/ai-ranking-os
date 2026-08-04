from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from decision_center import service
from decision_center.schemas import (
    AgentCreate,
    AgentRead,
    SprintCreate,
    SprintRead,
    TaskAssign,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)

router = APIRouter(tags=["decision-center"])
DbSession = Annotated[Session, Depends(get_db)]


def _not_found(error: service.EntityNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


def _conflict(error: service.RuleViolationError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(db: DbSession) -> list[TaskRead]:
    return service.list_tasks(db)


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: DbSession) -> TaskRead:
    try:
        return service.get_task(db, task_id)
    except service.EntityNotFoundError as error:
        raise _not_found(error) from error


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DbSession) -> TaskRead:
    try:
        return service.create_task(db, payload)
    except service.EntityNotFoundError as error:
        raise _not_found(error) from error
    except service.RuleViolationError as error:
        raise _conflict(error) from error


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, db: DbSession) -> TaskRead:
    try:
        return service.update_task(db, task_id, payload)
    except service.EntityNotFoundError as error:
        raise _not_found(error) from error
    except service.RuleViolationError as error:
        raise _conflict(error) from error


@router.post("/tasks/{task_id}/assign", response_model=TaskRead)
def assign_task(task_id: int, payload: TaskAssign, db: DbSession) -> TaskRead:
    try:
        return service.assign_task(db, task_id, payload)
    except service.EntityNotFoundError as error:
        raise _not_found(error) from error
    except service.RuleViolationError as error:
        raise _conflict(error) from error


@router.post("/tasks/{task_id}/complete", response_model=TaskRead)
def complete_task(task_id: int, db: DbSession) -> TaskRead:
    try:
        return service.complete_task(db, task_id)
    except service.EntityNotFoundError as error:
        raise _not_found(error) from error
    except service.RuleViolationError as error:
        raise _conflict(error) from error


@router.get("/agents", response_model=list[AgentRead])
def list_agents(db: DbSession) -> list[AgentRead]:
    return service.list_agents(db)


@router.post("/agents", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, db: DbSession) -> AgentRead:
    try:
        return service.create_agent(db, payload)
    except service.RuleViolationError as error:
        raise _conflict(error) from error


@router.get("/sprints", response_model=list[SprintRead])
def list_sprints(db: DbSession) -> list[SprintRead]:
    return service.list_sprints(db)


@router.post("/sprints", response_model=SprintRead, status_code=status.HTTP_201_CREATED)
def create_sprint(payload: SprintCreate, db: DbSession) -> SprintRead:
    try:
        return service.create_sprint(db, payload)
    except service.EntityNotFoundError as error:
        raise _not_found(error) from error
    except service.RuleViolationError as error:
        raise _conflict(error) from error
