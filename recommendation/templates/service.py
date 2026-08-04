from sqlalchemy.orm import Session

from recommendation.repository import RecommendationRepository
from recommendation.schemas import RecommendationRead
from recommendation.templates.repository import RecommendationTemplateRepository
from recommendation.templates.schemas import ActionPlan, ActionPlanItem


class ActionPlanService:
    """Read-only assembly of a persisted Recommendation set and templates."""

    def __init__(self, db: Session) -> None:
        self.recommendations = RecommendationRepository(db)
        self.templates = RecommendationTemplateRepository(db)

    def get(self, research_id: int) -> ActionPlan:
        execution = self.recommendations.latest_execution(research_id)
        items = [
            ActionPlanItem(
                recommendation=RecommendationRead.model_validate(recommendation),
                template=(
                    recommendation.template
                    if recommendation.template is not None
                    else None
                ),
                steps=(
                    recommendation.template.steps
                    if recommendation.template is not None
                    else []
                ),
                expected_effect=(
                    recommendation.template.expected_result
                    if recommendation.template is not None
                    else recommendation.expected_effect
                ),
                estimated_time=(
                    recommendation.template.estimated_time
                    if recommendation.template is not None
                    else None
                ),
            )
            for recommendation in execution.recommendations
        ]
        return ActionPlan(
            research_id=research_id,
            recommendation_execution_id=execution.id,
            engine_version=execution.engine_version,
            generated_at=execution.finished_at or execution.started_at,
            items=items,
        )
