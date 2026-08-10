from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ChangeSnapshot:
    research_id: int
    metrics: dict[str, float] = field(default_factory=dict)
    recommendations: frozenset[str] = frozenset()
    sources: frozenset[str] = frozenset()
    graph_nodes: frozenset[str] = frozenset()
    graph_edges: frozenset[str] = frozenset()


class ChangeSnapshotSource(Protocol):
    def pair(self, research_id: int) -> tuple[ChangeSnapshot | None, ChangeSnapshot]: ...


class ChangeDetectorPort(Protocol):
    def detect(self, research_id: int): ...
