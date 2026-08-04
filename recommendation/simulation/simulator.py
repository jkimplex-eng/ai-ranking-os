import math
import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from recommendation.models import Recommendation
from recommendation.ports import ResearchScoreSource
from recommendation.repository import RecommendationRepository
from recommendation.simulation.models import RecommendationSimulation
from recommendation.simulation.repository import RecommendationSimulationRepository
from recommendation.simulation.schemas import (
    RecommendationSimulationRead,
    SimulationResult,
)

MODEL_VERSION = "1.0"
SCORING_V1_WEIGHTS = {
    "mention_score": 0.35,
    "recommendation_score": 0.20,
    "citation_score": 0.15,
    "coverage_score": 0.20,
    "confidence_score": 0.10,
}
DURATION_PATTERN = re.compile(
    r"(?P<minimum>\d+)(?:\s*-\s*(?P<maximum>\d+))?\s*"
    r"(?P<unit>day|week|month)s?",
    re.IGNORECASE,
)
UNIT_DAYS = {"day": 1, "week": 7, "month": 30}


class ImpactSimulator:
    """Reproducible rule/weight model independent of Research persistence."""

    def __init__(
        self,
        db: Session,
        score_source: ResearchScoreSource,
    ) -> None:
        self.db = db
        self.score_source = score_source
        self.recommendations = RecommendationRepository(db)
        self.simulations = RecommendationSimulationRepository(db)

    def simulate(self, research_id: int) -> SimulationResult:
        snapshot = self.score_source.get_latest(research_id)
        execution = self.recommendations.latest_execution(research_id)
        simulated_at = datetime.now(UTC)
        rows = [
            self._simulate_recommendation(
                recommendation,
                current_visibility=snapshot.visibility_score,
                created_at=simulated_at,
            )
            for recommendation in execution.recommendations
        ]
        self.db.add_all(rows)
        self.db.commit()
        for row in rows:
            self.db.refresh(row)
        result_time = _as_utc(rows[0].created_at) if rows else simulated_at
        return _result(execution.id, research_id, result_time, rows)

    def get_latest(self, research_id: int) -> SimulationResult:
        execution, rows = self.simulations.latest(research_id)
        simulated_at = (
            _as_utc(rows[0].created_at)
            if rows
            else execution.finished_at or execution.started_at
        )
        return _result(execution.id, research_id, simulated_at, rows)

    @staticmethod
    def _simulate_recommendation(
        recommendation: Recommendation,
        *,
        current_visibility: float,
        created_at: datetime,
    ) -> RecommendationSimulation:
        target = (
            recommendation.rule.threshold
            if recommendation.rule is not None
            else recommendation.metric_value
        )
        metric_gap = max(target - recommendation.metric_value, 0.0)
        weight = SCORING_V1_WEIGHTS.get(recommendation.metric, 0.0)
        minimum_gain = metric_gap * 0.50 * weight
        expected_gain = metric_gap * 0.75 * weight
        maximum_gain = metric_gap * weight
        predicted = _bounded(current_visibility + expected_gain)
        return RecommendationSimulation(
            recommendation_id=recommendation.id,
            current_visibility=_bounded(current_visibility),
            predicted_visibility=predicted,
            predicted_delta=_bounded(predicted - current_visibility),
            confidence_min=_bounded(current_visibility + minimum_gain),
            confidence_expected=predicted,
            confidence_max=_bounded(current_visibility + maximum_gain),
            estimated_duration_days=_duration_days(recommendation),
            model_version=MODEL_VERSION,
            created_at=created_at,
        )


def _duration_days(recommendation: Recommendation) -> int:
    value = (
        recommendation.template.estimated_time
        if recommendation.template is not None
        else "30 days"
    )
    match = DURATION_PATTERN.search(value)
    if match is None:
        return 30
    minimum = int(match.group("minimum"))
    maximum = int(match.group("maximum") or minimum)
    multiplier = UNIT_DAYS[match.group("unit").casefold()]
    return max(1, math.ceil((minimum + maximum) / 2 * multiplier))


def _result(
    execution_id: int,
    research_id: int,
    simulated_at: datetime,
    rows: list[RecommendationSimulation],
) -> SimulationResult:
    return SimulationResult(
        research_id=research_id,
        recommendation_execution_id=execution_id,
        model_version=MODEL_VERSION,
        simulated_at=simulated_at,
        simulations=[_read(row) for row in rows],
    )


def _read(row: RecommendationSimulation) -> RecommendationSimulationRead:
    recommendation = row.recommendation
    target = (
        recommendation.rule.threshold
        if recommendation.rule is not None
        else recommendation.metric_value
    )
    return RecommendationSimulationRead(
        id=row.id,
        recommendation_id=row.recommendation_id,
        recommendation_type=recommendation.recommendation_type,
        metric=recommendation.metric,
        current_metric=recommendation.metric_value,
        expected_metric_change=round(
            max(target - recommendation.metric_value, 0.0) * 0.75,
            2,
        ),
        current_visibility=row.current_visibility,
        predicted_visibility=row.predicted_visibility,
        predicted_delta=row.predicted_delta,
        confidence_min=row.confidence_min,
        confidence_expected=row.confidence_expected,
        confidence_max=row.confidence_max,
        estimated_duration_days=row.estimated_duration_days,
        model_version=row.model_version,
        created_at=_as_utc(row.created_at),
    )


def _bounded(value: float) -> float:
    return round(max(0.0, min(value, 100.0)), 2)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
