from sqlalchemy.orm import Session

from research.reporting import ReportingService
from research.schemas import ResearchComparisonRead, ResearchReportRead


class ComparisonNotReadyError(ValueError):
    """Both researches must have a persisted score before comparison."""


class ComparisonService:
    """Read-only comparison of two persisted Research reports."""

    def __init__(self, db: Session) -> None:
        self.reporting = ReportingService(db)

    def compare(self, left_id: int, right_id: int) -> ResearchComparisonRead:
        left = self.reporting.get_report(left_id)
        right = self.reporting.get_report(right_id)
        if left.score is None or right.score is None:
            raise ComparisonNotReadyError(
                "Both researches must have a score before comparison"
            )
        left_entities = _entity_map(left)
        right_entities = _entity_map(right)
        left_recommendations = _recommendation_map(left)
        right_recommendations = _recommendation_map(right)
        return ResearchComparisonRead(
            left_research_id=left_id,
            right_research_id=right_id,
            left_score_version=left.score.version,
            right_score_version=right.score.version,
            visibility_score_delta=_delta(
                left.score.visibility_score,
                right.score.visibility_score,
            ),
            mention_score_delta=_delta(
                left.score.mention_score,
                right.score.mention_score,
            ),
            recommendation_score_delta=_delta(
                left.score.recommendation_score,
                right.score.recommendation_score,
            ),
            citation_score_delta=_delta(
                left.score.citation_score,
                right.score.citation_score,
            ),
            coverage_score_delta=_delta(
                left.score.coverage_score,
                right.score.coverage_score,
            ),
            confidence_score_delta=_delta(
                left.score.confidence_score,
                right.score.confidence_score,
            ),
            new_entities=_added(left_entities, right_entities),
            disappeared_entities=_added(right_entities, left_entities),
            new_recommendations=_added(
                left_recommendations,
                right_recommendations,
            ),
            disappeared_recommendations=_added(
                right_recommendations,
                left_recommendations,
            ),
        )


def _entity_map(report: ResearchReportRead) -> dict[str, str]:
    return {
        f"{entity.entity_type.casefold()}:{entity.canonical_name.casefold()}": (
            entity.canonical_name
        )
        for entity in report.entities
    }


def _recommendation_map(report: ResearchReportRead) -> dict[str, str]:
    return {
        recommendation.content.strip().casefold(): recommendation.content.strip()
        for recommendation in report.recommendations
    }


def _added(previous: dict[str, str], current: dict[str, str]) -> list[str]:
    return sorted(
        (current[key] for key in current.keys() - previous.keys()),
        key=str.casefold,
    )


def _delta(left: float, right: float) -> float:
    return round(right - left, 2)
