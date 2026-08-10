from typing import Protocol


class NotificationPort(Protocol):
    def emit(
        self,
        event_type: str,
        title: str,
        message: str,
        *,
        user_id: int = 1,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
        channels: tuple[str, ...] = ("UI",),
    ): ...


class DeliveryPort(Protocol):
    def send(self, channel: str, recipient: str, subject: str, message: str) -> str: ...
