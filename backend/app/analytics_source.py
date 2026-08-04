from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from analytics.ports import AnalyticsDataSource, AnalyticsRecord
from research.models import Research, ResearchScore


class PlatformAnalyticsDataSource(AnalyticsDataSource):
    """Platform integration adapter; keeps Research outside the analytics module."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def records(
        self, date_from: datetime | None = None, date_to: datetime | None = None
    ) -> list[AnalyticsRecord]:
        latest = aliased(ResearchScore)
        latest_id = (
            select(func.max(ResearchScore.id))
            .where(ResearchScore.research_id == Research.id)
            .correlate(Research)
            .scalar_subquery()
        )
        statement = select(Research, latest).join(
            latest,
            and_(latest.research_id == Research.id, latest.id == latest_id),
        )
        if date_from is not None:
            statement = statement.where(latest.calculated_at >= date_from)
        if date_to is not None:
            statement = statement.where(latest.calculated_at <= date_to)
        rows = self.db.execute(statement.order_by(latest.calculated_at, Research.id)).all()
        return [
            AnalyticsRecord(
                observed_at=score.calculated_at,
                dimensions={
                    "entity_id": str(research.entity_id or ""),
                    "research_id": str(research.id),
                    "status": research.status.value,
                    "algorithm_version": score.version,
                },
                metrics={
                    "visibility": score.visibility_score,
                    "mention": score.mention_score,
                    "recommendation": score.recommendation_score,
                    "citation": score.citation_score,
                    "coverage": score.coverage_score,
                    "confidence": score.confidence_score,
                },
            )
            for research, score in rows
        ]
