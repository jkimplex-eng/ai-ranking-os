import statistics
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from research.models import (
    Research,
    ResearchScore,
    ResearchTask,
    Response,
    ResponseProcessingStatus,
)
from research.schemas import (
    ResearchHistoryAggregates,
    ResearchHistoryItem,
    ResearchHistoryPagination,
    ResearchHistoryRead,
)


class ResearchHistoryService:
    """Read-only chronological history for one tracked entity."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_history(
        self,
        entity_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> ResearchHistoryRead:
        total = self.db.scalar(
            select(func.count(Research.id)).where(
                Research.entity_id == entity_id
            )
        ) or 0
        latest_score = aliased(ResearchScore)
        latest_score_at = (
            select(func.max(ResearchScore.calculated_at))
            .where(ResearchScore.research_id == Research.id)
            .correlate(Research)
            .scalar_subquery()
        )
        model_count = (
            select(func.count(func.distinct(ResearchTask.model)))
            .where(ResearchTask.research_id == Research.id)
            .correlate(Research)
            .scalar_subquery()
        )
        processed_count = (
            select(func.count(Response.id))
            .join(ResearchTask, ResearchTask.id == Response.research_task_id)
            .where(
                ResearchTask.research_id == Research.id,
                Response.processing_status == ResponseProcessingStatus.PROCESSED,
            )
            .correlate(Research)
            .scalar_subquery()
        )
        rows = self.db.execute(
            select(
                Research,
                latest_score.visibility_score,
                latest_score.version,
                model_count.label("model_count"),
                processed_count.label("processed_count"),
            )
            .outerjoin(
                latest_score,
                and_(
                    latest_score.research_id == Research.id,
                    latest_score.calculated_at == latest_score_at,
                ),
            )
            .where(Research.entity_id == entity_id)
            .order_by(Research.created_at.desc(), Research.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        items = [
            ResearchHistoryItem(
                research_id=research.id,
                created_at=research.created_at,
                status=research.status,
                visibility_score=visibility_score,
                score_version=version,
                model_count=model_total,
                processed_response_count=response_total,
            )
            for (
                research,
                visibility_score,
                version,
                model_total,
                response_total,
            ) in rows
        ]
        scored_history = self.db.execute(
            select(Research.created_at, Research.id, latest_score.visibility_score)
            .join(
                latest_score,
                and_(
                    latest_score.research_id == Research.id,
                    latest_score.calculated_at == latest_score_at,
                ),
            )
            .where(Research.entity_id == entity_id)
            .order_by(Research.created_at, Research.id)
        ).all()
        values = [float(row.visibility_score) for row in scored_history]
        aggregates = ResearchHistoryAggregates(
            best_visibility=max(values) if values else None,
            latest_visibility=values[-1] if values else None,
            average_visibility=(
                round(statistics.fmean(values), 2) if values else None
            ),
            research_count=total,
            first_to_latest_change=(
                round(values[-1] - values[0], 2) if values else None
            ),
        )
        return ResearchHistoryRead(
            entity_id=entity_id,
            items=items,
            aggregates=aggregates,
            pagination=ResearchHistoryPagination(
                offset=offset,
                limit=limit,
                total=total,
            ),
        )
