from dataclasses import dataclass, field
from typing import Protocol

from backend.app.llm_router.schemas import RoutingProfile


@dataclass(frozen=True)
class ResearchLaunchRequest:
    project_id: int
    domain_id: int | None
    title: str
    query: str
    routing_profile: RoutingProfile
    languages: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    template_code: str = "ai-visibility"


@dataclass(frozen=True)
class ResearchLaunchReceipt:
    research_id: int
    job_id: int
    state: str


class ResearchLaunchPort(Protocol):
    def launch(self, request: ResearchLaunchRequest) -> ResearchLaunchReceipt: ...
