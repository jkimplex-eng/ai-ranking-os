from sqlalchemy import select
from sqlalchemy.orm import Session

from research.models import (
    ExtractedCitation,
    ExtractedEntity,
    ExtractedRecommendation,
    Research,
    ResearchScore,
    ResearchTask,
    Response,
)
from research.repositories import EntityNotFoundError
from research.schemas import ResearchReportRead


class ReportingService:
    """Read-only aggregation of already persisted Research results."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_report(self, research_id: int) -> ResearchReportRead:
        research = self.db.get(Research, research_id)
        if research is None:
            raise EntityNotFoundError(f"Research {research_id} not found")
        response_ids = select(Response.id).join(ResearchTask).where(
            ResearchTask.research_id == research_id
        )
        responses = list(
            self.db.scalars(
                select(Response)
                .join(ResearchTask)
                .where(ResearchTask.research_id == research_id)
                .order_by(Response.id)
            )
        )
        score = self.db.scalar(
            select(ResearchScore)
            .where(ResearchScore.research_id == research_id)
            .order_by(ResearchScore.calculated_at.desc())
        )
        entities = list(
            self.db.scalars(
                select(ExtractedEntity)
                .where(ExtractedEntity.response_id.in_(response_ids))
                .order_by(ExtractedEntity.id)
            )
        )
        citations = list(
            self.db.scalars(
                select(ExtractedCitation)
                .where(ExtractedCitation.response_id.in_(response_ids))
                .order_by(
                    ExtractedCitation.response_id,
                    ExtractedCitation.position,
                    ExtractedCitation.id,
                )
            )
        )
        recommendations = list(
            self.db.scalars(
                select(ExtractedRecommendation)
                .where(ExtractedRecommendation.response_id.in_(response_ids))
                .order_by(
                    ExtractedRecommendation.response_id,
                    ExtractedRecommendation.rank,
                    ExtractedRecommendation.id,
                )
            )
        )
        return ResearchReportRead(
            research=research,
            score=score,
            responses=responses,
            entities=entities,
            citations=citations,
            recommendations=recommendations,
        )
