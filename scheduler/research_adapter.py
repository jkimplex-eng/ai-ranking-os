from sqlalchemy.orm import Session

from research.models import Research, ResearchStatus
from research.repositories import ResearchRepository
from research.schemas import ResearchCreate, ResearchModelSelection, ResearchRunRequest
from research.service import run_research
from scheduler.engine import SchedulerEngine
from scheduler.ports import (
    ResearchLauncher,
    ResearchLaunchRequest,
    ResearchLaunchResult,
    ResearchTemplateNotFoundError,
)


class SqlAlchemyResearchLauncher(ResearchLauncher):
    """Research integration adapter; Scheduler core imports no Research code."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def launch(self, request: ResearchLaunchRequest) -> ResearchLaunchResult:
        template = self.db.get(Research, request.template_research_id)
        if template is None:
            raise ResearchTemplateNotFoundError(
                f"Research template {request.template_research_id} not found"
            )
        clone = ResearchRepository(self.db).create(
            ResearchCreate(
                entity_id=template.entity_id,
                project_id=template.project_id,
                domain_id=template.domain_id,
                title=template.title,
                description=template.description,
                objective=template.objective,
                metadata={
                    **template.metadata_payload,
                    "scheduled_from_research_id": template.id,
                },
            )
        )
        result = run_research(
            self.db,
            clone.id,
            ResearchRunRequest(
                models=[
                    ResearchModelSelection(provider=item.provider, model=item.model)
                    for item in request.models
                ],
                query=request.query,
            ),
        )
        return ResearchLaunchResult(
            research_id=result.id,
            succeeded=result.status == ResearchStatus.COMPLETED,
            error=(None if result.status == ResearchStatus.COMPLETED else "Research failed"),
        )


def build_scheduler_engine(db: Session) -> SchedulerEngine:
    return SchedulerEngine(db, SqlAlchemyResearchLauncher(db))
