from typing import Any, Protocol


class DeadLetterQueue(Protocol):
    def publish(self, queue: str, payload: dict[str, Any], error: str, attempts: int) -> int: ...


class FailoverProvider(Protocol):
    def execute(self, operation: str, payload: dict[str, Any]) -> Any: ...
