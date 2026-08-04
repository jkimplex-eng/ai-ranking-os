from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from relationship_discovery.models import (
    RelationshipDecisionType,
    RelationshipStatus,
    RelationshipType,
)


class DiscoveryRunRequest(BaseModel):
    snapshot_id: int | None = Field(default=None, ge=1)


class RelationshipEvidenceRead(BaseModel):
    id: int
    source_type: str
    source_reference: str
    confidence: float = Field(ge=0, le=1)
    payload: dict[str, Any]
    created_at: datetime


class RelationshipDecisionRead(BaseModel):
    id: int
    decision: RelationshipDecisionType
    actor: str
    reason: str | None
    algorithm_version: str
    created_at: datetime


class RelationshipCandidateRead(BaseModel):
    id: int
    graph_snapshot_id: int
    source_external_id: str
    target_external_id: str
    relationship_type: RelationshipType
    confidence: float = Field(ge=0, le=1)
    status: RelationshipStatus
    algorithm_version: str
    integrated_snapshot_id: int | None
    created_at: datetime
    resolved_at: datetime | None
    evidence: list[RelationshipEvidenceRead]
    decisions: list[RelationshipDecisionRead]


class DiscoveryRunResult(BaseModel):
    graph_snapshot_id: int
    algorithm_version: str
    candidate_count: int = Field(ge=0)
    candidates: list[RelationshipCandidateRead]


class RelationshipDecisionRequest(BaseModel):
    actor: str = Field(default="manual", min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=2000)
