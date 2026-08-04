from execution_engine.models import ExecutionState


class InvalidExecutionTransitionError(ValueError):
    """Raised when an execution state transition is not allowed."""


ALLOWED_TRANSITIONS: dict[ExecutionState, frozenset[ExecutionState]] = {
    ExecutionState.PENDING: frozenset(
        {ExecutionState.ASSIGNED, ExecutionState.CANCELLED, ExecutionState.FAILED}
    ),
    ExecutionState.ASSIGNED: frozenset(
        {ExecutionState.RUNNING, ExecutionState.CANCELLED, ExecutionState.FAILED}
    ),
    ExecutionState.RUNNING: frozenset(
        {
            ExecutionState.WAITING_REVIEW,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
        }
    ),
    ExecutionState.WAITING_REVIEW: frozenset(
        {ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED}
    ),
    ExecutionState.COMPLETED: frozenset(),
    ExecutionState.FAILED: frozenset(),
    ExecutionState.CANCELLED: frozenset(),
}


def transition(current: ExecutionState, target: ExecutionState) -> ExecutionState:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidExecutionTransitionError(f"Cannot transition from {current} to {target}")
    return target

