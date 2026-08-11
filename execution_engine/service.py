import os
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from decision_center.models import (
    Agent,
    ExecutionLog,
    Task,
    TaskPriority,
    TaskStatus,
)
from execution_engine.models import Execution, ExecutionState
from execution_engine.state_machine import InvalidExecutionTransitionError, transition
from execution_engine.worker_manager import WorkerManager

MAX_RETRIES = 3
MAX_ATTEMPTS = 1 + MAX_RETRIES
ACTIVE_STATES = (
    ExecutionState.PENDING,
    ExecutionState.ASSIGNED,
    ExecutionState.RUNNING,
    ExecutionState.WAITING_REVIEW,
)
priority_order = case(
    (Task.priority == TaskPriority.HIGH, 0),
    (Task.priority == TaskPriority.MEDIUM, 1),
    else_=2,
)


class ExecutionEngineError(Exception):
    """Base Execution Engine error."""


class QueueEmptyError(ExecutionEngineError):
    """No READY task is available."""


class NoAgentAvailableError(ExecutionEngineError):
    """No compatible idle agent is available."""


class ExecutionNotFoundError(ExecutionEngineError):
    """Requested execution does not exist."""


class ExecutionConflictError(ExecutionEngineError):
    """Execution cannot perform the requested operation."""


def _now() -> datetime:
    return datetime.now(UTC)


def _log(
    db: Session,
    execution: Execution,
    action: str,
    changes: dict[str, Any],
) -> None:
    db.add(
        ExecutionLog(
            entity_type="Execution",
            entity_id=execution.id,
            action=action,
            changes=changes,
        )
    )


def _set_state(db: Session, execution: Execution, target: ExecutionState) -> None:
    previous = execution.state
    try:
        execution.state = transition(previous, target)
    except InvalidExecutionTransitionError as error:
        raise ExecutionConflictError(str(error)) from error
    _log(
        db,
        execution,
        "STATE_TRANSITION",
        {"before": {"state": previous}, "after": {"state": target}},
    )


def list_queue(db: Session) -> list[Task]:
    query = (
        select(Task)
        .where(Task.status == TaskStatus.READY)
        .order_by(priority_order, Task.created_at, Task.id)
    )
    return list(db.scalars(query))


def _select_ready_task(db: Session) -> Task:
    query = (
        select(Task)
        .where(Task.status == TaskStatus.READY)
        .order_by(priority_order, Task.created_at, Task.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    task = db.scalar(query)
    if task is None:
        raise QueueEmptyError("No READY tasks in the queue")
    return task


def _select_task(db: Session, task_id: int) -> Task:
    query = (
        select(Task)
        .where(Task.id == task_id, Task.status == TaskStatus.READY)
        .with_for_update(skip_locked=True)
    )
    task = db.scalar(query)
    if task is None:
        raise QueueEmptyError(f"Task {task_id} is not READY or does not exist")
    return task


def _select_agent(db: Session, task: Task, manager: WorkerManager) -> Agent:
    cutoff = _now() - timedelta(seconds=float(os.getenv("EXECUTION_STALE_SECONDS", "900")))
    stale = list(
        db.scalars(
            select(Execution).where(
                Execution.state.in_(ACTIVE_STATES),
                Execution.started_at.is_not(None),
                Execution.started_at < cutoff,
            )
        )
    )
    for execution in stale:
        execution.state = ExecutionState.FAILED
        execution.error = "Execution expired after worker interruption"
        _finish(execution)
        stale_task = db.get(Task, execution.task_id)
        if stale_task is not None:
            stale_task.status = TaskStatus.BLOCKED
            stale_task.owner_id = None
        _log(db, execution, "STALE_EXECUTION_RECOVERED", {"cutoff": cutoff.isoformat()})
    if stale:
        db.commit()
    active_task = exists().where(
        Task.owner_id == Agent.id,
        Task.status == TaskStatus.IN_PROGRESS,
    )
    active_execution = exists().where(
        Execution.agent_id == Agent.id,
        Execution.state.in_(ACTIVE_STATES),
    )
    query = (
        select(Agent)
        .where(
            Agent.is_enabled.is_(True),
            Agent.agent_type.in_(manager.supported_types),
            ~active_task,
            ~active_execution,
        )
        .order_by(Agent.id)
        .with_for_update(skip_locked=True)
    )
    if task.required_specialization is not None:
        query = query.where(Agent.specialization == task.required_specialization)
    else:
        query = query.where(Agent.specialization.is_(None))

    agent = db.scalar(query.limit(1))
    if agent is None:
        raise NoAgentAvailableError("No compatible free agent is available")
    return agent


def schedule_execution(
    db: Session,
    manager: WorkerManager,
) -> tuple[Execution, Task, Agent]:
    task = _select_ready_task(db)
    agent = _select_agent(db, task, manager)
    execution = Execution(task_id=task.id, state=ExecutionState.PENDING)
    db.add(execution)
    db.flush()
    _log(db, execution, "CREATE", {"after": {"state": ExecutionState.PENDING}})
    execution.agent_id = agent.id
    _set_state(db, execution, ExecutionState.ASSIGNED)
    task.owner_id = agent.id
    task.status = TaskStatus.IN_PROGRESS
    db.add(
        ExecutionLog(
            entity_type="Task",
            entity_id=task.id,
            action="EXECUTION_ASSIGN",
            changes={
                "after": {
                    "owner_id": agent.id,
                    "status": TaskStatus.IN_PROGRESS,
                    "execution_id": execution.id,
                }
            },
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise NoAgentAvailableError("Task or agent was claimed concurrently") from error
    db.refresh(execution)
    return execution, task, agent


def schedule_task_execution(
    db: Session,
    task_id: int,
    manager: WorkerManager,
) -> tuple[Execution, Task, Agent]:
    task = _select_task(db, task_id)
    agent = _select_agent(db, task, manager)
    execution = Execution(task_id=task.id, state=ExecutionState.PENDING)
    db.add(execution)
    db.flush()
    _log(db, execution, "CREATE", {"after": {"state": ExecutionState.PENDING}})
    execution.agent_id = agent.id
    _set_state(db, execution, ExecutionState.ASSIGNED)
    task.owner_id = agent.id
    task.status = TaskStatus.IN_PROGRESS
    db.add(
        ExecutionLog(
            entity_type="Task",
            entity_id=task.id,
            action="EXECUTION_ASSIGN",
            changes={
                "after": {
                    "owner_id": agent.id,
                    "status": TaskStatus.IN_PROGRESS,
                    "execution_id": execution.id,
                }
            },
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise NoAgentAvailableError("Task or agent was claimed concurrently") from error
    db.refresh(execution)
    return execution, task, agent


def _finish(execution: Execution) -> None:
    execution.finished_at = _now()
    if execution.started_at is not None:
        started_at = execution.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        execution.duration_ms = max(
            0,
            int((execution.finished_at - started_at).total_seconds() * 1000),
        )


def run_execution(
    db: Session,
    execution: Execution,
    task: Task,
    agent: Agent,
    manager: WorkerManager,
    *,
    retry_base_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
) -> Execution:
    _set_state(db, execution, ExecutionState.RUNNING)
    execution.started_at = _now()
    db.commit()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        execution.attempt_count = attempt
        try:
            execution.result = manager.execute(agent.agent_type, task)
            execution.error = None
        except Exception as error:
            execution.error = str(error)
            _log(
                db,
                execution,
                "ATTEMPT_FAILED",
                {"attempt": attempt, "reason": str(error)},
            )
            db.commit()
            if attempt < MAX_ATTEMPTS:
                delay = retry_base_seconds * (2 ** (attempt - 1))
                sleep(delay)
                continue

            _set_state(db, execution, ExecutionState.FAILED)
            task.status = TaskStatus.BLOCKED
            _finish(execution)
            db.add(
                ExecutionLog(
                    entity_type="Task",
                    entity_id=task.id,
                    action="EXECUTION_FAILED",
                    changes={"reason": execution.error, "attempts": attempt},
                )
            )
            db.commit()
            db.refresh(execution)
            return execution

        _set_state(db, execution, ExecutionState.WAITING_REVIEW)
        task.status = TaskStatus.REVIEW
        db.flush()
        _set_state(db, execution, ExecutionState.COMPLETED)
        task.status = TaskStatus.DONE
        _finish(execution)
        db.add(
            ExecutionLog(
                entity_type="Task",
                entity_id=task.id,
                action="EXECUTION_COMPLETED",
                changes={
                    "before": {"status": TaskStatus.REVIEW},
                    "after": {"status": TaskStatus.DONE},
                    "attempts": attempt,
                },
            )
        )
        db.commit()
        db.refresh(execution)
        return execution

    raise AssertionError("Retry loop must return a terminal execution")


def start_next_execution(
    db: Session,
    manager: WorkerManager,
    *,
    retry_base_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
) -> Execution:
    execution, task, agent = schedule_execution(db, manager)
    return run_execution(
        db,
        execution,
        task,
        agent,
        manager,
        retry_base_seconds=retry_base_seconds,
        sleep=sleep,
    )


def start_task_execution(
    db: Session,
    task_id: int,
    manager: WorkerManager,
    *,
    retry_base_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
) -> Execution:
    execution, task, agent = schedule_task_execution(db, task_id, manager)
    return run_execution(
        db,
        execution,
        task,
        agent,
        manager,
        retry_base_seconds=retry_base_seconds,
        sleep=sleep,
    )


def cancel_execution(db: Session, execution_id: int) -> Execution:
    execution = db.get(Execution, execution_id)
    if execution is None:
        raise ExecutionNotFoundError(f"Execution {execution_id} not found")
    if execution.state not in ACTIVE_STATES:
        raise ExecutionConflictError(f"Execution in {execution.state} cannot be cancelled")

    task = db.get(Task, execution.task_id)
    _set_state(db, execution, ExecutionState.CANCELLED)
    _finish(execution)
    if task is not None:
        task.status = TaskStatus.READY
        task.owner_id = None
        db.add(
            ExecutionLog(
                entity_type="Task",
                entity_id=task.id,
                action="EXECUTION_CANCELLED",
                changes={"after": {"status": TaskStatus.READY, "owner_id": None}},
            )
        )
    db.commit()
    db.refresh(execution)
    return execution


def get_execution(db: Session, execution_id: int) -> Execution:
    execution = db.get(Execution, execution_id)
    if execution is None:
        raise ExecutionNotFoundError(f"Execution {execution_id} not found")
    return execution


def list_history(db: Session) -> list[Execution]:
    query = select(Execution).order_by(
        Execution.created_at.desc(),
        Execution.id.desc(),
    )
    return list(db.scalars(query))
