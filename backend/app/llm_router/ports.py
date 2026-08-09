from enum import StrEnum
from typing import Any, Protocol

from sqlalchemy.orm import Session

from backend.app.llm_router.schemas import RouteRequest


class ProviderState(StrEnum):
    READY = "READY"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    DISABLED = "DISABLED"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderReadinessPort(Protocol):
    def state(self, provider_id: str) -> ProviderState: ...


class ModelEvaluationPort(Protocol):
    def scores(self, task_type: str | None) -> dict[str, float]: ...


class LLMRouterPort(Protocol):
    def generate(self, db: Session, request: RouteRequest) -> dict[str, Any]: ...
