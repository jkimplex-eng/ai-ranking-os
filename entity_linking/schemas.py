from datetime import datetime

from pydantic import BaseModel, Field

from entity_linking.models import LinkDecisionType, LinkStatus


class LinkingRunRequest(BaseModel):
    snapshot_id: int | None = Field(default=None, ge=1)


class LinkDecisionRead(BaseModel):
    id: int
    decision: LinkDecisionType
    canonical_entity_id: int | None
    actor: str
    reason: str | None
    algorithm_version: str
    created_at: datetime


class LinkCandidateRead(BaseModel):
    id: int
    graph_snapshot_id: int
    graph_node_id: int
    external_id: str
    entity_name: str
    normalized_name: str
    entity_type: str
    canonical_entity_id: int | None
    canonical_name: str | None
    confidence: float = Field(ge=0, le=1)
    match_method: str
    status: LinkStatus
    algorithm_version: str
    created_at: datetime
    resolved_at: datetime | None
    decisions: list[LinkDecisionRead]


class LinkingRunResult(BaseModel):
    graph_snapshot_id: int
    algorithm_version: str
    total: int = Field(ge=0)
    approved: int = Field(ge=0)
    pending: int = Field(ge=0)
    candidates: list[LinkCandidateRead]


class CandidateDecisionRequest(BaseModel):
    canonical_entity_id: int | None = Field(default=None, ge=1)
    actor: str = Field(default="manual", min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=2000)
