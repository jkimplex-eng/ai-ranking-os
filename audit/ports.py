from typing import Any, Protocol


class AuditWriter(Protocol):
    def record(
        self,
        *,
        actor_id: str,
        action: str,
        category: str,
        resource: str,
        correlation_id: str,
        actor_type: str = "user",
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        old_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
    ): ...
