from datetime import UTC, datetime

from sqlalchemy.orm import Session

from recommendation.models import (
    Recommendation,
    RecommendationExecution,
    RecommendationExecutionStatus,
    RecommendationRule,
)
from recommendation.ports import ResearchScoreSource
from recommendation.repository import RecommendationRepository
from recommendation.schemas import RecommendationRead, RecommendationSet
from recommendation.templates.models import RecommendationTemplate
from recommendation.templates.repository import RecommendationTemplateRepository

ENGINE_VERSION = "1.0"
PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


class UnsupportedRuleOperatorError(ValueError):
    """A persisted rule uses an operator unknown to this engine version."""


class RecommendationEngine:
    """Rule-only engine depending on a score-source port, not Research."""

    def __init__(
        self,
        db: Session,
        score_source: ResearchScoreSource,
    ) -> None:
        self.db = db
        self.score_source = score_source
        self.repository = RecommendationRepository(db)
        self.template_repository = RecommendationTemplateRepository(db)

    def generate(self, research_id: int) -> RecommendationSet:
        snapshot = self.score_source.get_latest(research_id)
        input_snapshot = {
            "score_version": snapshot.version,
            "metrics": snapshot.metrics(),
        }
        execution = RecommendationExecution(
            research_id=research_id,
            status=RecommendationExecutionStatus.RUNNING,
            engine_version=ENGINE_VERSION,
            input_snapshot=input_snapshot,
        )
        self.db.add(execution)
        self.db.flush()
        try:
            templates = self.template_repository.by_type(ENGINE_VERSION)
            recommendations = [
                self._recommendation(
                    execution,
                    rule,
                    value,
                    templates.get(rule.recommendation_type),
                )
                for rule in self.repository.active_rules(ENGINE_VERSION)
                if _matches(rule, value := snapshot.metrics()[rule.metric])
            ]
            self.db.add_all(recommendations)
            execution.generated_count = len(recommendations)
            execution.status = RecommendationExecutionStatus.COMPLETED
            execution.finished_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(execution)
            return _to_set(execution)
        except Exception as error:
            self.db.rollback()
            failed = RecommendationExecution(
                research_id=research_id,
                status=RecommendationExecutionStatus.FAILED,
                engine_version=ENGINE_VERSION,
                input_snapshot=input_snapshot,
                error=str(error),
                finished_at=datetime.now(UTC),
            )
            self.db.add(failed)
            self.db.commit()
            raise

    def get_latest(self, research_id: int) -> RecommendationSet:
        return _to_set(self.repository.latest_execution(research_id))

    @staticmethod
    def _recommendation(
        execution: RecommendationExecution,
        rule: RecommendationRule,
        value: float,
        template: RecommendationTemplate | None,
    ) -> Recommendation:
        return Recommendation(
            execution_id=execution.id,
            rule_id=rule.id,
            template_id=template.id if template is not None else None,
            research_id=execution.research_id,
            recommendation_type=rule.recommendation_type,
            priority=rule.priority,
            explanation=rule.explanation_template.format(
                metric=rule.metric,
                metric_value=round(value, 2),
                threshold=rule.threshold,
            ),
            metric=rule.metric,
            metric_value=value,
            expected_effect=rule.expected_effect,
        )


def _matches(rule: RecommendationRule, value: float) -> bool:
    operators = {
        "lt": value < rule.threshold,
        "lte": value <= rule.threshold,
        "gt": value > rule.threshold,
        "gte": value >= rule.threshold,
    }
    try:
        return operators[rule.operator]
    except KeyError as error:
        raise UnsupportedRuleOperatorError(
            f"Unsupported rule operator: {rule.operator}"
        ) from error


def _to_set(execution: RecommendationExecution) -> RecommendationSet:
    recommendations = sorted(
        execution.recommendations,
        key=lambda item: (PRIORITY_ORDER[str(item.priority)], item.id),
    )
    return RecommendationSet(
        execution_id=execution.id,
        research_id=execution.research_id,
        status=execution.status,
        engine_version=execution.engine_version,
        score_version=str(execution.input_snapshot["score_version"]),
        generated_at=execution.finished_at or execution.started_at,
        recommendations=[
            RecommendationRead.model_validate(item) for item in recommendations
        ],
    )
