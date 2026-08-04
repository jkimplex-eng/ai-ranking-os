from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from alert.engine import AlertEngine
from alert.ports import AlertDataSource, AlertObservation
from recommendation.models import Recommendation, RecommendationPriority
from research.models import (
    ExtractedCitation,
    ExtractedRecommendation,
    Research,
    ResearchScore,
    ResearchTask,
    Response,
)


class SqlAlchemyAlertDataSource(AlertDataSource):
    """Infrastructure adapter translating persisted research into alert inputs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def history(self, entity_id: UUID) -> list[AlertObservation]:
        latest_score_id = (
            select(func.max(ResearchScore.id))
            .where(ResearchScore.research_id == Research.id)
            .correlate(Research)
            .scalar_subquery()
        )
        score_rows = self.db.execute(
            select(Research.id, Research.created_at, ResearchScore)
            .join(ResearchScore, ResearchScore.id == latest_score_id)
            .where(Research.entity_id == entity_id)
            .order_by(Research.created_at, Research.id)
        ).all()
        research_ids = [research_id for research_id, _, _ in score_rows]
        if not research_ids:
            return []

        brand_recommendations: dict[int, set[str]] = defaultdict(set)
        authoritative_citations: dict[int, set[str]] = defaultdict(set)
        critical_recommendations: dict[int, set[str]] = defaultdict(set)
        recommendation_rows = self.db.execute(
            select(ResearchTask.research_id, ExtractedRecommendation.content)
            .join(Response, Response.research_task_id == ResearchTask.id)
            .join(ExtractedRecommendation, ExtractedRecommendation.response_id == Response.id)
            .where(ResearchTask.research_id.in_(research_ids))
        ).all()
        for research_id, content in recommendation_rows:
            brand_recommendations[research_id].add(content.strip())

        citation_rows = self.db.execute(
            select(
                ResearchTask.research_id,
                ExtractedCitation.url,
                ExtractedCitation.source,
                ExtractedCitation.title,
                ExtractedCitation.metadata_payload,
            )
            .join(Response, Response.research_task_id == ResearchTask.id)
            .join(ExtractedCitation, ExtractedCitation.response_id == Response.id)
            .where(ResearchTask.research_id.in_(research_ids))
        ).all()
        for research_id, url, source, title, metadata in citation_rows:
            if self._is_authoritative(metadata):
                identity = (url or source or title or "").strip()
                if identity:
                    authoritative_citations[research_id].add(identity)

        critical_rows = self.db.execute(
            select(Recommendation.research_id, Recommendation.explanation).where(
                Recommendation.research_id.in_(research_ids),
                Recommendation.priority == RecommendationPriority.CRITICAL,
            )
        ).all()
        for research_id, explanation in critical_rows:
            critical_recommendations[research_id].add(explanation.strip())

        return [
            AlertObservation(
                research_id=research_id,
                observed_at=observed_at,
                visibility=score.visibility_score,
                confidence=score.confidence_score,
                brand_recommendations=frozenset(brand_recommendations[research_id]),
                authoritative_citations=frozenset(authoritative_citations[research_id]),
                critical_recommendations=frozenset(critical_recommendations[research_id]),
            )
            for research_id, observed_at, score in score_rows
        ]

    @staticmethod
    def _is_authoritative(metadata: dict[str, Any]) -> bool:
        if metadata.get("authoritative") is True:
            return True
        score = metadata.get("authority_score")
        return isinstance(score, int | float) and not isinstance(score, bool) and score >= 0.7


def build_alert_engine(db: Session) -> AlertEngine:
    return AlertEngine(db, SqlAlchemyAlertDataSource(db))

