from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class SearchNode:
    internal_id: int
    entity_id: str
    name: str
    canonical_name: str
    node_type: str
    confidence: float
    aliases: tuple[str, ...] = ()
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchEdge:
    edge_id: int
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence: float
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchGraph:
    snapshot_id: int
    nodes: tuple[SearchNode, ...]
    edges: tuple[SearchEdge, ...]


class GraphProvider(Protocol):
    """Public read-only graph contract consumed by Graph Search."""

    def latest_graph(self) -> SearchGraph: ...
