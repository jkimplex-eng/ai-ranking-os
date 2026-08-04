from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from analytics.ports import AnalyticsDataSource, AnalyticsRecord
from research.models import Research, ResearchScore, ResearchTask


class PlatformSegmentationDataSource(AnalyticsDataSource):
    """Integration adapter that exposes supported segmentation dimensions."""

    DIMENSIONS = ("brand", "category", "country", "marketplace", "source", "language")

    def __init__(self, db: Session) -> None:
        self.db = db

    def records(
        self, date_from: datetime | None = None, date_to: datetime | None = None
    ) -> list[AnalyticsRecord]:
        latest_score = aliased(ResearchScore)
        latest_score_id = (
            select(func.max(ResearchScore.id))
            .where(ResearchScore.research_id == Research.id)
            .correlate(Research)
            .scalar_subquery()
        )
        latest_model = (
            select(ResearchTask.model)
            .where(ResearchTask.research_id == Research.id, ResearchTask.model.is_not(None))
            .order_by(ResearchTask.id.desc())
            .limit(1)
            .correlate(Research)
            .scalar_subquery()
        )
        statement = select(Research, latest_score, latest_model.label("model")).join(
            latest_score,
            and_(latest_score.research_id == Research.id, latest_score.id == latest_score_id),
        )
        if date_from is not None:
            statement = statement.where(latest_score.calculated_at >= date_from)
        if date_to is not None:
            statement = statement.where(latest_score.calculated_at <= date_to)
        return [
            AnalyticsRecord(
                observed_at=score.calculated_at,
                dimensions={
                    "entity_id": str(research.entity_id or ""),
                    "research_id": str(research.id),
                    "model": model or str(research.metadata_payload.get("model", "")),
                    **{key: str(research.metadata_payload.get(key, "")) for key in self.DIMENSIONS},
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
            for research, score, model in self.db.execute(statement).all()
        ]
