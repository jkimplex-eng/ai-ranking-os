import statistics
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research.models import (
    Research,
    ResearchScore,
    ResearchTask,
    Response,
    ResponseProcessingStatus,
)
from research.repositories import EntityNotFoundError

SCORING_VERSION = "1.2"
SCORING_WEIGHTS = {
    "mention": 0.35,
    "recommendation": 0.20,
    "citation": 0.15,
    "coverage": 0.20,
    "confidence": 0.10,
}


class ScoringNotReadyError(ValueError):
    """Research does not yet have enough processed responses."""


class ScoringService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def calculate(self, research_id: int) -> ResearchScore:
        research = self.db.get(Research, research_id)
        if research is None:
            raise EntityNotFoundError(f"Research {research_id} not found")
        responses = self._responses(research_id)
        if not responses:
            raise ScoringNotReadyError(f"Research {research_id} has no responses to score")
        if any(
            response.processing_status == ResponseProcessingStatus.NORMALIZED
            for response in responses
        ):
            raise ScoringNotReadyError(f"Research {research_id} still has unprocessed responses")

        processed = [
            response
            for response in responses
            if response.processing_status == ResponseProcessingStatus.PROCESSED
        ]
        target = self._target(research)
        mention_score = _ratio(
            sum(self._mentions(response, target) for response in processed),
            len(responses),
        )
        recommendation_score = _ratio(
            sum(self._recommends_target(response, target) for response in processed),
            len(responses),
        )
        citation_score = _ratio(
            sum(len(response.extracted_citations) for response in processed),
            len(responses) * 3,
        )
        expected = max(research.total_tasks, len(research.tasks), 1)
        coverage_score = _ratio(len(processed), expected)
        entity_confidences = [
            entity.confidence for response in processed for entity in response.extracted_entities
        ]
        entity_confidence = (
            statistics.fmean(entity_confidences) * 100 if entity_confidences else 50.0
        )
        processing_success = _ratio(len(processed), len(responses))
        sample_factor = min(1.0, len(processed) / 8)
        confidence_score = _bounded(
            processing_success * 0.5 + entity_confidence * 0.3 + sample_factor * 100 * 0.2
        )
        visibility_score = _bounded(
            mention_score * SCORING_WEIGHTS["mention"]
            + recommendation_score * SCORING_WEIGHTS["recommendation"]
            + citation_score * SCORING_WEIGHTS["citation"]
            + coverage_score * SCORING_WEIGHTS["coverage"]
            + confidence_score * SCORING_WEIGHTS["confidence"]
        )

        score = self.db.scalar(
            select(ResearchScore).where(
                ResearchScore.research_id == research_id,
                ResearchScore.version == SCORING_VERSION,
            )
        )
        if score is None:
            score = ResearchScore(
                research_id=research_id,
                version=SCORING_VERSION,
            )
            self.db.add(score)
        score.mention_score = mention_score
        score.recommendation_score = recommendation_score
        score.citation_score = citation_score
        score.coverage_score = coverage_score
        score.confidence_score = confidence_score
        score.visibility_score = visibility_score
        score.calculated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(score)
        return score

    def get(self, research_id: int) -> ResearchScore:
        if self.db.get(Research, research_id) is None:
            raise EntityNotFoundError(f"Research {research_id} not found")
        score = self.db.scalar(
            select(ResearchScore)
            .where(ResearchScore.research_id == research_id)
            .order_by(ResearchScore.calculated_at.desc())
        )
        if score is None:
            raise EntityNotFoundError(f"Score for Research {research_id} not found")
        return score

    def calculate_if_ready(self, research_id: int) -> ResearchScore | None:
        research = self.db.get(Research, research_id)
        if research is None or research.total_tasks <= 0:
            return None
        responses = self._responses(research_id)
        if len(responses) < research.total_tasks:
            return None
        if any(
            response.processing_status == ResponseProcessingStatus.NORMALIZED
            for response in responses
        ):
            return None
        return self.calculate(research_id)

    def _responses(self, research_id: int) -> list[Response]:
        return list(
            self.db.scalars(
                select(Response)
                .join(ResearchTask)
                .where(ResearchTask.research_id == research_id)
                .options(
                    selectinload(Response.extracted_entities),
                    selectinload(Response.extracted_citations),
                    selectinload(Response.extracted_recommendations),
                )
                .order_by(Response.id)
            )
        )

    @staticmethod
    def _target(research: Research) -> str:
        metadata = research.metadata_payload
        for key in ("target_entity", "entity", "brand"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().casefold()
        return research.title.strip().casefold()

    @staticmethod
    def _mentions(response: Response, target: str) -> bool:
        if target in response.content.casefold():
            return True
        return any(
            target
            in {
                entity.name.casefold(),
                entity.canonical_name.casefold(),
                *(alias.casefold() for alias in entity.aliases),
            }
            for entity in response.extracted_entities
        )

    @staticmethod
    def _recommends_target(response: Response, target: str) -> bool:
        """Count only recommendations that explicitly name the measured brand.

        Generic product/category advice is useful evidence, but it is not a brand
        recommendation and must not inflate the target's recommendation score.
        """
        return any(target in item.content.casefold() for item in response.extracted_recommendations)


def response_recommends_target(response: Response, target: str) -> bool:
    """Public scoring predicate reused by explainability/report composition."""
    return ScoringService._recommends_target(response, target.casefold())


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return _bounded(numerator / denominator * 100)


def _bounded(value: float) -> float:
    return round(max(0.0, min(value, 100.0)), 2)
