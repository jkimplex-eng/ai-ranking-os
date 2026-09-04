from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class AliceEvidenceRecord:
    research_id: int
    response_id: int
    brand: str
    query: str
    category: str
    language: str
    region: str
    provider: str
    model: str
    mentioned: bool
    recommended: bool
    cited: bool
    recommendation_rank: int | None
    source_domains: list[str]
    features: dict[str, float]
    feature_evidence: dict
    evidence_status: str
    observed_at: datetime


class AliceEvidencePort(Protocol):
    def records(self, organization_id: int, research_id: int) -> list[AliceEvidenceRecord]: ...


class ConfirmedInfluencePort(Protocol):
    def factors(self, *, category: str, language: str, region: str) -> list[dict]: ...
