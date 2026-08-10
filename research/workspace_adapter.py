from sqlalchemy import select
from sqlalchemy.orm import Session

from research.models import Research
from research.ports import ResearchLaunchReceipt, ResearchLaunchRequest
from research.queue import enqueue
from research.repositories import ResearchRepository
from research.schemas import ResearchCreate, ResearchEnqueueRequest


class SqlAlchemyResearchLauncher:
    """Research-owned adapter implementing the product workspace launch port."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def launch(self, request: ResearchLaunchRequest) -> ResearchLaunchReceipt:
        research = ResearchRepository(self.db).create(
            ResearchCreate(
                project_id=request.project_id,
                domain_id=request.domain_id,
                title=request.title,
                objective=request.query,
                metadata={
                    "template_code": request.template_code,
                    "languages": request.languages,
                    "regions": request.regions,
                },
            )
        )
        job = enqueue(
            self.db,
            ResearchEnqueueRequest(
                research_id=research.id,
                routing_profile=request.routing_profile,
                query=request.query,
            ),
        )
        return ResearchLaunchReceipt(
            research_id=research.id,
            job_id=job.id,
            state=job.state,
        )

    def statuses(self, research_ids: list[int]) -> dict[int, str]:
        if not research_ids:
            return {}
        rows = self.db.execute(
            select(Research.id, Research.status).where(Research.id.in_(research_ids))
        )
        return {
            research_id: status.value if hasattr(status, "value") else str(status)
            for research_id, status in rows
        }
