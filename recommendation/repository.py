from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from recommendation.models import (
    Recommendation,
    RecommendationExecution,
    RecommendationExecutionStatus,
    RecommendationRule,
)


class RecommendationSetNotFoundError(LookupError):
    """No completed Recommendation set exists for a Research ID."""


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def active_rules(self, version: str) -> list[RecommendationRule]:
        return list(
            self.db.scalars(
                select(RecommendationRule)
                .where(
                    RecommendationRule.is_active.is_(True),
                    RecommendationRule.version == version,
                )
                .order_by(RecommendationRule.id)
            )
        )

    def latest_execution(self, research_id: int) -> RecommendationExecution:
        execution = self.db.scalar(
            select(RecommendationExecution)
            .where(
                RecommendationExecution.research_id == research_id,
                RecommendationExecution.status
                == RecommendationExecutionStatus.COMPLETED,
            )
            .options(
                selectinload(
                    RecommendationExecution.recommendations
                ).selectinload(Recommendation.template),
                selectinload(
                    RecommendationExecution.recommendations
                ).selectinload(Recommendation.rule),
            )
            .order_by(
                RecommendationExecution.finished_at.desc(),
                RecommendationExecution.id.desc(),
            )
        )
        if execution is None:
            raise RecommendationSetNotFoundError(
                f"Recommendations for Research {research_id} not found"
            )
        return execution
