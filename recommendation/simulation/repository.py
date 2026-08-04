from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from recommendation.models import Recommendation, RecommendationExecution
from recommendation.repository import RecommendationRepository
from recommendation.simulation.models import RecommendationSimulation


class RecommendationSimulationNotFoundError(LookupError):
    """No simulation exists for the latest Recommendation set."""


class RecommendationSimulationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.recommendations = RecommendationRepository(db)

    def latest(
        self,
        research_id: int,
    ) -> tuple[RecommendationExecution, list[RecommendationSimulation]]:
        execution = self.recommendations.latest_execution(research_id)
        recommendation_ids = [item.id for item in execution.recommendations]
        if not recommendation_ids:
            return execution, []
        latest_created_at = self.db.scalar(
            select(func.max(RecommendationSimulation.created_at)).where(
                RecommendationSimulation.recommendation_id.in_(
                    recommendation_ids
                )
            )
        )
        if latest_created_at is None:
            raise RecommendationSimulationNotFoundError(
                f"Simulation for Research {research_id} not found"
            )
        simulations = list(
            self.db.scalars(
                select(RecommendationSimulation)
                .where(
                    RecommendationSimulation.recommendation_id.in_(
                        recommendation_ids
                    ),
                    RecommendationSimulation.created_at == latest_created_at,
                )
                .options(
                    selectinload(
                        RecommendationSimulation.recommendation
                    ).selectinload(Recommendation.rule),
                    selectinload(
                        RecommendationSimulation.recommendation
                    ).selectinload(Recommendation.template),
                )
                .order_by(RecommendationSimulation.id)
            )
        )
        return execution, simulations
