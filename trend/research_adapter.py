from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from research.models import Research, ResearchScore
from trend.ports import TrendDataSource, TrendObservation

if TYPE_CHECKING:
    from trend.engine import TrendEngine


class SqlAlchemyTrendDataSource(TrendDataSource):
    """Research-specific adapter kept outside the trend domain core."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def history(self, entity_id: UUID) -> list[TrendObservation]:
        latest_score = aliased(ResearchScore)
        latest_score_id = (
            select(func.max(ResearchScore.id))
            .where(ResearchScore.research_id == Research.id)
            .correlate(Research)
            .scalar_subquery()
        )
        rows = self.db.execute(
            select(Research.id, Research.created_at, latest_score)
            .join(
                latest_score,
                and_(
                    latest_score.research_id == Research.id,
                    latest_score.id == latest_score_id,
                ),
            )
            .where(Research.entity_id == entity_id)
            .order_by(Research.created_at, Research.id)
        ).all()
        return [
            TrendObservation(
                research_id=research_id,
                observed_at=observed_at,
                visibility=score.visibility_score,
                mention=score.mention_score,
                recommendation=score.recommendation_score,
                citation=score.citation_score,
                coverage=score.coverage_score,
                confidence=score.confidence_score,
            )
            for research_id, observed_at, score in rows
        ]


def build_trend_engine(db: Session) -> "TrendEngine":
    from trend.engine import TrendEngine

    return TrendEngine(db, SqlAlchemyTrendDataSource(db))
