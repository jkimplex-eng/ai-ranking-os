from sqlalchemy import select
from sqlalchemy.orm import Session

from provider_recommendation.ports import ProviderUsageFact
from research.models import ResearchTask, Response


class SqlAlchemyResearchUsageSource:
    def __init__(self, db: Session) -> None:
        self.db = db

    def usage(self, research_id: int) -> list[ProviderUsageFact]:
        rows = self.db.execute(
            select(Response, ResearchTask)
            .join(ResearchTask, Response.research_task_id == ResearchTask.id)
            .where(ResearchTask.research_id == research_id)
        )
        return [
            ProviderUsageFact(
                provider=response.provider,
                model=response.model,
                latency_ms=float(response.latency_ms or 0),
                cost=float(response.cost),
                tokens=response.total_tokens,
            )
            for response, _ in rows
        ]
