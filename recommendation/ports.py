from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ResearchScoreSnapshot:
    research_id: int
    version: str
    mention_score: float
    recommendation_score: float
    citation_score: float
    coverage_score: float
    confidence_score: float
    visibility_score: float

    def metrics(self) -> dict[str, float]:
        return {
            "mention_score": self.mention_score,
            "recommendation_score": self.recommendation_score,
            "citation_score": self.citation_score,
            "coverage_score": self.coverage_score,
            "confidence_score": self.confidence_score,
            "visibility_score": self.visibility_score,
        }


class ResearchScoreSource(Protocol):
    def get_latest(self, research_id: int) -> ResearchScoreSnapshot: ...


class ResearchNotFoundError(LookupError):
    """The requested Research ID does not exist."""


class ResearchScoreUnavailableError(ValueError):
    """No score is available for the requested Research ID."""
