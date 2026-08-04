import time
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Event, Lock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.providers.models import ProviderUsageRecord
from query_executor.dispatcher import Dispatcher
from query_executor.executor import InMemoryTelemetry, execute_plan
from query_executor.models import (
    QueryExecutionHistory,
    QueryExecutionMetric,
    QueryProviderMetric,
)
from query_executor.schemas import (
    CancellationResult,
    ExecutionPlan,
    ExecutorResult,
    ExecutorState,
    StepState,
)


class ExecutorNotFoundError(LookupError):
    """No executor history exists for the execution ID."""


class ExecutorConflictError(ValueError):
    """The requested executor operation conflicts with its state."""


dispatcher = Dispatcher()
_active_cancellations: dict[str, Event] = {}
_active_lock = Lock()


def _register(execution_id: str, cancellation: Event) -> None:
    with _active_lock:
        _active_cancellations[execution_id] = cancellation


def _unregister(execution_id: str) -> None:
    with _active_lock:
        _active_cancellations.pop(execution_id, None)


def run(
    db: Session,
    plan: ExecutionPlan,
    *,
    provider_dispatcher: Dispatcher | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> ExecutorResult:
    execution_id = str(uuid4())
    cancellation = Event()
    row = QueryExecutionHistory(
        execution_id=execution_id,
        plan_id=plan.plan_id or "",
        request_id=plan.request_id,
        mode=plan.mode,
        state=ExecutorState.PENDING,
        plan_payload=plan.model_dump(mode="json"),
        output_payload=None,
        created_at=datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _register(execution_id, cancellation)
    row.state = ExecutorState.RUNNING
    db.commit()
    try:
        telemetry = InMemoryTelemetry()
        result = execute_plan(
            execution_id,
            plan,
            provider_dispatcher or dispatcher,
            cancellation=cancellation,
            telemetry=telemetry,
            sleep=sleep,
        )
        row.state = result.state
        row.output_payload = result.model_dump(mode="json")
        row.error = result.error
        row.started_at = result.started_at
        row.finished_at = result.finished_at
        row.duration_ms = result.duration_ms
        failures = sum(
            item.state
            in {StepState.FAILED, StepState.TIMED_OUT, StepState.CANCELLED}
            for item in result.results
        )
        db.add_all(
            [
                QueryExecutionMetric(
                    execution_row_id=row.id,
                    execution_id=execution_id,
                    metric_name="duration",
                    metric_value=result.duration_ms,
                    unit="ms",
                    metadata_payload={},
                ),
                QueryExecutionMetric(
                    execution_row_id=row.id,
                    execution_id=execution_id,
                    metric_name="failures",
                    metric_value=failures,
                    unit="count",
                    metadata_payload={},
                ),
                QueryExecutionMetric(
                    execution_row_id=row.id,
                    execution_id=execution_id,
                    metric_name="telemetry_events",
                    metric_value=result.telemetry["event_count"],
                    unit="count",
                    metadata_payload={},
                ),
            ]
        )
        db.add_all(
            [
                QueryProviderMetric(
                    execution_row_id=row.id,
                    execution_id=execution_id,
                    step_id=item.step_id,
                    provider=item.provider,
                    state=item.state,
                    attempts=item.attempts,
                    latency_ms=item.latency_ms,
                    failure=item.error,
                )
                for item in result.results
            ]
        )
        for item in result.results:
            output = item.output if isinstance(item.output, dict) else {}
            usage = output.get("usage", {}) if isinstance(output, dict) else {}
            if usage:
                db.add(
                    ProviderUsageRecord(
                        execution_id=execution_id,
                        provider=str(usage["provider"]),
                        model=str(usage["model"]),
                        prompt_tokens=int(usage["prompt_tokens"]),
                        completion_tokens=int(usage["completion_tokens"]),
                        total_tokens=int(usage["total_tokens"]),
                        estimated_cost=float(usage["estimated_cost"]),
                        currency=str(usage["currency"]),
                        created_at=datetime.fromisoformat(usage["timestamp"]),
                    )
                )
        db.commit()
        return result
    finally:
        _unregister(execution_id)


def get_result(db: Session, execution_id: str) -> ExecutorResult:
    query = select(QueryExecutionHistory).where(
        QueryExecutionHistory.execution_id == execution_id
    )
    row = db.scalar(query)
    if row is None:
        raise ExecutorNotFoundError(f"No query execution {execution_id}")
    if row.output_payload is None:
        raise ExecutorConflictError(f"Execution {execution_id} has not finished")
    return ExecutorResult.model_validate(row.output_payload)


def cancel(db: Session, execution_id: str) -> CancellationResult:
    query = select(QueryExecutionHistory).where(
        QueryExecutionHistory.execution_id == execution_id
    )
    row = db.scalar(query)
    if row is None:
        raise ExecutorNotFoundError(f"No query execution {execution_id}")
    if row.state not in {ExecutorState.PENDING, ExecutorState.RUNNING}:
        raise ExecutorConflictError(f"Execution in {row.state} cannot be cancelled")
    with _active_lock:
        cancellation = _active_cancellations.get(execution_id)
        if cancellation is not None:
            cancellation.set()
    row.state = ExecutorState.CANCELLED
    db.commit()
    return CancellationResult(
        execution_id=execution_id,
        state=ExecutorState.CANCELLED,
    )
