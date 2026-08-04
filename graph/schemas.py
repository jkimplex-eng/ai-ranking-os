from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GraphBuildRequest(BaseModel):
    source_ids: list[str] = Field(default_factory=list, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphNodeRead(BaseModel):
    id: int
    external_id: str
    name: str
    canonical_name: str
    node_type: str
    confidence: float = Field(ge=0, le=1)
    aliases: list[str]
    properties: dict[str, Any]


class GraphEdgeRead(BaseModel):
    id: int
    source_node_id: int
    target_node_id: int
    edge_type: str
    confidence: float = Field(ge=0, le=1)
    properties: dict[str, Any]


class GraphSnapshotRead(BaseModel):
    id: int
    structure_version: str
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    build_metadata: dict[str, Any]
    created_at: datetime
    nodes: list[GraphNodeRead]
    edges: list[GraphEdgeRead]

