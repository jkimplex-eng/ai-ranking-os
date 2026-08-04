from sqlalchemy import select
from sqlalchemy.orm import Session

from recommendation.ports import (
    ResearchNotFoundError,
    ResearchScoreSnapshot,
    ResearchScoreSource,
    ResearchScoreUnavailableError,
)
from research.models import Research, ResearchScore


class SqlAlchemyResearchScoreAdapter(ResearchScoreSource):
    """Infrastructure adapter; the engine itself does not import Research."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_latest(self, research_id: int) -> ResearchScoreSnapshot:
        if self.db.get(Research, research_id) is None:
            raise ResearchNotFoundError(
                f"Research {research_id} not found"
            )
        score = self.db.scalar(
            select(ResearchScore)
            .where(ResearchScore.research_id == research_id)
            .order_by(
                ResearchScore.calculated_at.desc(),
                ResearchScore.id.desc(),
            )
        )
        if score is None:
            raise ResearchScoreUnavailableError(
                f"Research {research_id} has no score"
            )
        return ResearchScoreSnapshot(
            research_id=research_id,
            version=score.version,
            mention_score=score.mention_score,
            recommendation_score=score.recommendation_score,
            citation_score=score.citation_score,
            coverage_score=score.coverage_score,
            confidence_score=score.confidence_score,
            visibility_score=score.visibility_score,
        )
