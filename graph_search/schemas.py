from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TraversalDirection(StrEnum):
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"
    BOTH = "BOTH"


class GraphSearchNodeRead(BaseModel):
    internal_id: int
    entity_id: str
    name: str
    canonical_name: str
    node_type: str
    confidence: float = Field(ge=0, le=1)
    aliases: list[str]
    properties: dict[str, Any]


class GraphSearchEdgeRead(BaseModel):
    edge_id: int
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence: float = Field(ge=0, le=1)
    properties: dict[str, Any]


class GraphSearchResult(BaseModel):
    snapshot_id: int
    query: str | None
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    items: list[GraphSearchNodeRead]
    relationships: list[GraphSearchEdgeRead]


class NeighborRead(BaseModel):
    depth: int = Field(ge=1, le=5)
    node: GraphSearchNodeRead


class GraphNeighborsResult(BaseModel):
    snapshot_id: int
    root: GraphSearchNodeRead
    direction: TraversalDirection
    max_depth: int = Field(ge=1, le=5)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    items: list[NeighborRead]
    traversed_relationships: list[GraphSearchEdgeRead]
