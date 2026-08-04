import time
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Event, Lock
from typing import Any, Protocol

from backend.app.providers.metrics import RETRIES
from query_executor.dispatcher import Dispatcher
from query_executor.parallel_executor import execute_parallel
from query_executor.planner import validate_plan
from query_executor.result_collector import (
    collect_ensemble,
    collect_fallback,
    collect_parallel,
    collect_single,
)
from query_executor.retry import ExecutionCancelledError, execute_with_retry
from query_executor.schemas import (
    ExecutionMode,
    ExecutionPlan,
    ExecutorResult,
    ExecutorState,
    PlanStep,
    StepResult,
    StepState,
)
from query_executor.timeout import ProviderTimeoutError

DEFAULT_SLEEP = time.sleep


class TelemetryHook(Protocol):
    def emit(self, event: dict[str, Any]) -> None: ...


class InMemoryTelemetry:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._lock = Lock()

    def emit(self, event: dict[str, Any]) -> None:
        with self._lock:
            self.events.append(event)


def _duration_ms(started: datetime, finished: datetime) -> int:
    return max(0, int((finished - started).total_seconds() * 1000))


def _run_step(
    step: PlanStep,
    dispatcher: Dispatcher,
    cancellation: Event,
    telemetry: TelemetryHook,
    *,
    sleep: Callable[[float], None],
) -> StepResult:
    telemetry.emit({"event": "step_started", "step_id": step.step_id, "provider": step.provider})
    attempts_seen = 0

    def on_attempt(event: dict[str, Any]) -> None:
        nonlocal attempts_seen
        attempts_seen = int(event["attempt"])
        if attempts_seen > 1:
            RETRIES.labels(provider=step.provider).inc()
        telemetry.emit(
            {
                "event": "provider_attempt",
                "step_id": step.step_id,
                "provider": step.provider,
                **event,
            }
        )

    try:
        output, attempts, latency_ms = execute_with_retry(
            lambda: dispatcher.dispatch(step.provider, step.payload, cancellation),
            timeout_seconds=step.timeout_seconds,
            max_retries=step.max_retries,
            retry_base_seconds=step.retry_base_seconds,
            cancellation=cancellation,
            sleep=sleep,
            on_attempt=on_attempt,
        )
        result = StepResult(
            step_id=step.step_id,
            provider=step.provider,
            state=StepState.COMPLETED,
            attempts=attempts,
            latency_ms=latency_ms,
            output=output,
        )
    except ExecutionCancelledError as error:
        result = StepResult(
            step_id=step.step_id,
            provider=step.provider,
            state=StepState.CANCELLED,
            attempts=attempts_seen,
            latency_ms=0,
            error=str(error),
        )
    except ProviderTimeoutError as error:
        result = StepResult(
            step_id=step.step_id,
            provider=step.provider,
            state=StepState.TIMED_OUT,
            attempts=max(1, attempts_seen),
            latency_ms=int(step.timeout_seconds * 1000) * max(1, attempts_seen),
            error=str(error),
        )
    except Exception as error:
        result = StepResult(
            step_id=step.step_id,
            provider=step.provider,
            state=StepState.FAILED,
            attempts=max(1, attempts_seen),
            latency_ms=0,
            error=str(error),
        )
    telemetry.emit(
        {
            "event": "step_finished",
            "step_id": step.step_id,
            "provider": step.provider,
            "state": result.state,
        }
    )
    return result


def execute_plan(
    execution_id: str,
    plan: ExecutionPlan,
    dispatcher: Dispatcher,
    *,
    cancellation: Event | None = None,
    telemetry: TelemetryHook | None = None,
    sleep: Callable[[float], None] = DEFAULT_SLEEP,
) -> ExecutorResult:
    plan = validate_plan(plan)
    cancel_event = cancellation or Event()
    telemetry_hook = telemetry or InMemoryTelemetry()
    started = datetime.now(UTC)
    telemetry_hook.emit({"event": "execution_started", "execution_id": execution_id})

    def operation(step: PlanStep) -> StepResult:
        return _run_step(
            step,
            dispatcher,
            cancel_event,
            telemetry_hook,
            sleep=sleep,
        )
    if plan.mode in {
        ExecutionMode.PARALLEL,
        ExecutionMode.ENSEMBLE,
        ExecutionMode.CONSENSUS,
    }:
        results = execute_parallel(plan.steps, operation)
    elif plan.mode == ExecutionMode.FALLBACK:
        results = []
        for index, step in enumerate(plan.steps):
            result = operation(step)
            results.append(result)
            if result.state == StepState.COMPLETED:
                results.extend(
                    StepResult(
                        step_id=remaining.step_id,
                        provider=remaining.provider,
                        state=StepState.SKIPPED,
                        attempts=0,
                        latency_ms=0,
                    )
                    for remaining in plan.steps[index + 1 :]
                )
                break
            if cancel_event.is_set():
                break
    else:
        results = [operation(plan.steps[0])]

    completed = sum(result.state == StepState.COMPLETED for result in results)
    if cancel_event.is_set():
        state = ExecutorState.CANCELLED
    elif completed == len(plan.steps):
        state = ExecutorState.COMPLETED
    elif completed > 0:
        state = (
            ExecutorState.COMPLETED
            if plan.mode == ExecutionMode.FALLBACK
            else ExecutorState.PARTIAL
        )
    elif any(result.state == StepState.TIMED_OUT for result in results):
        state = ExecutorState.TIMED_OUT
    else:
        state = ExecutorState.FAILED

    collectors = {
        ExecutionMode.SINGLE: collect_single,
        ExecutionMode.PARALLEL: collect_parallel,
        ExecutionMode.ENSEMBLE: collect_ensemble,
        ExecutionMode.CONSENSUS: collect_ensemble,
        ExecutionMode.FALLBACK: collect_fallback,
    }
    output = collectors[plan.mode](results)
    finished = datetime.now(UTC)
    telemetry_hook.emit(
        {"event": "execution_finished", "execution_id": execution_id, "state": state}
    )
    events = getattr(telemetry_hook, "events", [])
    return ExecutorResult(
        execution_id=execution_id,
        plan_id=plan.plan_id or "",
        request_id=plan.request_id,
        mode=plan.mode,
        state=state,
        results=results,
        output=output,
        error=None if completed else next((item.error for item in results if item.error), None),
        started_at=started,
        finished_at=finished,
        duration_ms=_duration_ms(started, finished),
        telemetry={"event_count": len(events), "events": events},
    )
