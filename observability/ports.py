from typing import Protocol


class HealthCheck(Protocol):
    @property
    def name(self) -> str: ...
    def check(self) -> tuple[bool, str]: ...


class MetricsProvider(Protocol):
    def snapshot(self) -> dict[str, float | int]: ...
