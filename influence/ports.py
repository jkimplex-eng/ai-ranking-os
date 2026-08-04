from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class InfluenceNode:
    entity_id: str
    name: str
    node_type: str


@dataclass(frozen=True, slots=True)
class InfluenceEdge:
    source_entity_id: str
    target_entity_id: str
    weight: float


@dataclass(frozen=True, slots=True)
class InfluenceGraph:
    snapshot_id: int
    nodes: tuple[InfluenceNode, ...]
    edges: tuple[InfluenceEdge, ...]


class GraphProvider(Protocol):
    """Public read-only graph port required by influence scoring."""

    def latest_graph(self) -> InfluenceGraph: ...
