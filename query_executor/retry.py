import time
from collections.abc import Callable
from threading import Event
from time import perf_counter
from typing import Any

from query_executor.timeout import run_with_timeout


class ExecutionCancelledError(RuntimeError):
    """Execution was cancelled by its caller."""


def execute_with_retry(
    operation: Callable[[], Any],
    *,
    timeout_seconds: float,
    max_retries: int,
    retry_base_seconds: float,
    cancellation: Event,
    sleep: Callable[[float], None] = time.sleep,
    on_attempt: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[Any, int, int]:
    started = perf_counter()
    total_attempts = 1 + max_retries
    last_error: Exception | None = None
    for attempt in range(1, total_attempts + 1):
        if cancellation.is_set():
            raise ExecutionCancelledError("Execution was cancelled")
        try:
            output = run_with_timeout(operation, timeout_seconds)
            if on_attempt:
                on_attempt({"attempt": attempt, "status": "completed"})
            latency_ms = int((perf_counter() - started) * 1000)
            return output, attempt, latency_ms
        except Exception as error:
            last_error = error
            if on_attempt:
                on_attempt(
                    {
                        "attempt": attempt,
                        "status": "failed",
                        "error": str(error),
                    }
                )
            if attempt < total_attempts:
                sleep(retry_base_seconds * (2 ** (attempt - 1)))
    assert last_error is not None
    raise last_error
