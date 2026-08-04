from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from enum import StrEnum
from queue import Full, Queue
from threading import RLock
from time import monotonic, sleep
from typing import Any


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(RuntimeError):
    pass


class BackpressureError(RuntimeError):
    pass


class OperationTimeoutError(TimeoutError):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_seconds=30):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = 0.0
        self.lock = RLock()

    def execute(self, operation: Callable[[], Any]):
        with self.lock:
            if self.state == CircuitState.OPEN:
                if monotonic() - self.opened_at < self.recovery_seconds:
                    raise CircuitOpenError("Circuit is open")
                self.state = CircuitState.HALF_OPEN
        try:
            result = operation()
        except Exception:
            with self.lock:
                self.failures += 1
                if self.failures >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.opened_at = monotonic()
            raise
        with self.lock:
            self.failures = 0
            self.state = CircuitState.CLOSED
        return result


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    base_delay_seconds: float = 0.05
    max_delay_seconds: float = 2

    def execute(self, operation):
        for attempt in range(1, self.attempts + 1):
            try:
                return operation()
            except Exception:
                if attempt == self.attempts:
                    raise
                sleep(min(self.max_delay_seconds, self.base_delay_seconds * 2 ** (attempt - 1)))


def run_with_timeout(operation, seconds):
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(operation)
    try:
        return future.result(timeout=seconds)
    except FutureTimeout as error:
        future.cancel()
        raise OperationTimeoutError("Operation timed out") from error
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


class BackpressureGate:
    def __init__(self, capacity):
        self.queue = Queue(maxsize=capacity)

    def enter(self):
        try:
            self.queue.put_nowait(1)
        except Full as error:
            raise BackpressureError("Capacity exhausted") from error

    def leave(self):
        self.queue.get_nowait()
