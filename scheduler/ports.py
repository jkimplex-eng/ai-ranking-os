from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ScheduledModel:
    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class ResearchLaunchRequest:
    template_research_id: int
    models: tuple[ScheduledModel, ...]
    query: str | None


@dataclass(frozen=True, slots=True)
class ResearchLaunchResult:
    research_id: int
    succeeded: bool
    error: str | None = None


class ResearchLauncher(Protocol):
    """Public command boundary used by Scheduler Engine."""

    def launch(self, request: ResearchLaunchRequest) -> ResearchLaunchResult: ...


class ResearchTemplateNotFoundError(LookupError):
    """The configured research template no longer exists."""

