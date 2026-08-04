from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class DiscoveryEntity:
    external_id: str


@dataclass(frozen=True, slots=True)
class ExistingRelationship:
    source_external_id: str
    target_external_id: str
    relationship_type: str


@dataclass(frozen=True, slots=True)
class DiscoveryGraph:
    snapshot_id: int
    entities: tuple[DiscoveryEntity, ...]
    relationships: tuple[ExistingRelationship, ...]


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    source_external_id: str
    target_external_id: str
    relationship_type: str
    confidence: float
    source_type: str
    source_reference: str
    payload: dict[str, Any] = field(default_factory=dict)


class GraphProvider(Protocol):
    def graph(self, snapshot_id: int | None = None) -> DiscoveryGraph: ...

    def integrate(self, snapshot_id: int, evidence: EvidenceItem) -> int: ...


class EvidenceProvider(Protocol):
    def evidence(self, graph: DiscoveryGraph) -> list[EvidenceItem]: ...
