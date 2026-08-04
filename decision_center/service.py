from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from decision_center.models import Agent, ExecutionLog, Project, Sprint, Task, TaskStatus
from decision_center.schemas import AgentCreate, SprintCreate, TaskAssign, TaskCreate, TaskUpdate


class DecisionCenterError(Exception):
    """Base domain error."""


class EntityNotFoundError(DecisionCenterError):
    """Requested entity does not exist."""


class RuleViolationError(DecisionCenterError):
    """A Decision Center invariant would be violated."""


def _add_log(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    changes: dict[str, Any],
) -> None:
    db.add(
        ExecutionLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            changes=changes,
        )
    )


def _commit(db: Session, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise RuleViolationError(conflict_message) from error


def _flush(db: Session, conflict_message: str) -> None:
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise RuleViolationError(conflict_message) from error


def _get_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise EntityNotFoundError(f"Task {task_id} not found")
    return task


def _ensure_agent_available(
    db: Session,
    agent_id: int,
    *,
    except_task_id: int | None = None,
) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise EntityNotFoundError(f"Agent {agent_id} not found")

    query = select(Task.id).where(
        Task.owner_id == agent_id,
        Task.status == TaskStatus.IN_PROGRESS,
    )
    if except_task_id is not None:
        query = query.where(Task.id != except_task_id)
    if db.scalar(query) is not None:
        raise RuleViolationError("Agent already has an IN_PROGRESS task")
    return agent


def _validate_references(
    db: Session,
    *,
    sprint_id: int | None,
    project_id: int | None,
) -> None:
    if sprint_id is not None and db.get(Sprint, sprint_id) is None:
        raise EntityNotFoundError(f"Sprint {sprint_id} not found")
    if project_id is not None and db.get(Project, project_id) is None:
        raise EntityNotFoundError(f"Project {project_id} not found")


def list_tasks(db: Session) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.id)))


def get_task(db: Session, task_id: int) -> Task:
    return _get_task(db, task_id)


def create_task(db: Session, payload: TaskCreate) -> Task:
    _validate_references(db, sprint_id=payload.sprint_id, project_id=payload.project_id)
    if payload.owner_id is not None:
        if payload.status == TaskStatus.IN_PROGRESS:
            _ensure_agent_available(db, payload.owner_id)
        elif db.get(Agent, payload.owner_id) is None:
            raise EntityNotFoundError(f"Agent {payload.owner_id} not found")

    task = Task(**payload.model_dump())
    db.add(task)
    _flush(db, "Task conflicts with an existing active assignment")
    _add_log(
        db,
        entity_type="Task",
        entity_id=task.id,
        action="CREATE",
        changes={"after": payload.model_dump(mode="json")},
    )
    _commit(db, "Task conflicts with an existing active assignment")
    db.refresh(task)
    return task


def update_task(db: Session, task_id: int, payload: TaskUpdate) -> Task:
    task = _get_task(db, task_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return task

    if changes.get("status") == TaskStatus.DONE:
        raise RuleViolationError("Use the complete endpoint to move a task from REVIEW to DONE")
    _validate_references(
        db,
        sprint_id=changes.get("sprint_id"),
        project_id=changes.get("project_id"),
    )
    if changes.get("status") == TaskStatus.IN_PROGRESS and task.owner_id is not None:
        _ensure_agent_available(db, task.owner_id, except_task_id=task.id)

    before = {
        field: getattr(task, field).value
        if isinstance(getattr(task, field), TaskStatus)
        else getattr(task, field)
        for field in changes
    }
    for field, value in changes.items():
        setattr(task, field, value)
    _flush(db, "Agent already has an IN_PROGRESS task")
    _add_log(
        db,
        entity_type="Task",
        entity_id=task.id,
        action="UPDATE",
        changes={
            "before": before,
            "after": payload.model_dump(mode="json", exclude_unset=True),
        },
    )
    _commit(db, "Agent already has an IN_PROGRESS task")
    db.refresh(task)
    return task


def assign_task(db: Session, task_id: int, payload: TaskAssign) -> Task:
    task = _get_task(db, task_id)
    if task.status == TaskStatus.IN_PROGRESS:
        _ensure_agent_available(db, payload.agent_id, except_task_id=task.id)
    elif db.get(Agent, payload.agent_id) is None:
        raise EntityNotFoundError(f"Agent {payload.agent_id} not found")

    previous_owner_id = task.owner_id
    task.owner_id = payload.agent_id
    _flush(db, "Agent already has an IN_PROGRESS task")
    _add_log(
        db,
        entity_type="Task",
        entity_id=task.id,
        action="ASSIGN",
        changes={"before": {"owner_id": previous_owner_id}, "after": {"owner_id": task.owner_id}},
    )
    _commit(db, "Agent already has an IN_PROGRESS task")
    db.refresh(task)
    return task


def complete_task(db: Session, task_id: int) -> Task:
    task = _get_task(db, task_id)
    if task.status != TaskStatus.REVIEW:
        raise RuleViolationError("Task must be in REVIEW before it can be completed")

    task.status = TaskStatus.DONE
    _flush(db, "Could not complete task")
    _add_log(
        db,
        entity_type="Task",
        entity_id=task.id,
        action="COMPLETE",
        changes={"before": {"status": "REVIEW"}, "after": {"status": "DONE"}},
    )
    _commit(db, "Could not complete task")
    db.refresh(task)
    return task


def list_agents(db: Session) -> list[Agent]:
    return list(db.scalars(select(Agent).order_by(Agent.id)))


def create_agent(db: Session, payload: AgentCreate) -> Agent:
    agent = Agent(**payload.model_dump())
    db.add(agent)
    _flush(db, "Agent name must be unique")
    _add_log(
        db,
        entity_type="Agent",
        entity_id=agent.id,
        action="CREATE",
        changes={"after": payload.model_dump(mode="json")},
    )
    _commit(db, "Agent name must be unique")
    db.refresh(agent)
    return agent


def list_sprints(db: Session) -> list[Sprint]:
    return list(db.scalars(select(Sprint).order_by(Sprint.id)))


def create_sprint(db: Session, payload: SprintCreate) -> Sprint:
    _validate_references(db, sprint_id=None, project_id=payload.project_id)
    sprint = Sprint(**payload.model_dump())
    db.add(sprint)
    _flush(db, "Could not create sprint")
    _add_log(
        db,
        entity_type="Sprint",
        entity_id=sprint.id,
        action="CREATE",
        changes={"after": payload.model_dump(mode="json")},
    )
    _commit(db, "Could not create sprint")
    db.refresh(sprint)
    return sprint
