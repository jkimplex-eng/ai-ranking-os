from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AutomationLaunchRequest:
    owner_user_id: int
    template_research_id: int
    brand: str
    website_url: str
    language: str
    region: str
    research_profile: str
    routing_profile: str
    models: tuple[dict[str, str], ...]
    queries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AutomationLaunchResult:
    research_id: int
    succeeded: bool
    actual_cost_usd: float
    result: dict
    error: str | None = None


class AutomationResearchPort(Protocol):
    def launch(self, request: AutomationLaunchRequest) -> AutomationLaunchResult: ...


class AutomationNotificationPort(Protocol):
    def emit(self, event_type: str, title: str, message: str, **kwargs): ...


@dataclass(frozen=True, slots=True)
class AutomationTemplateContext:
    queries: tuple[dict, ...]
    metadata: dict


class AutomationTemplatePort(Protocol):
    def context(
        self, organization_id: int, template_research_id: int, website_url: str
    ) -> AutomationTemplateContext: ...
