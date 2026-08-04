from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LinkableEntity:
    graph_node_id: int
    external_id: str
    name: str
    canonical_name: str
    entity_type: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LinkableGraph:
    snapshot_id: int
    entities: tuple[LinkableEntity, ...]


@dataclass(frozen=True, slots=True)
class CanonicalRecord:
    id: int
    canonical_name: str
    normalized_name: str
    entity_type: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Resolution:
    canonical_entity_id: int | None
    confidence: float
    match_method: str


class GraphProvider(Protocol):
    def graph(self, snapshot_id: int | None = None) -> LinkableGraph: ...


class EntityResolver(Protocol):
    def resolve(self, entity: LinkableEntity, canonicals: list[CanonicalRecord]) -> Resolution: ...
