from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class GraphBuildContext:
    source_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProvidedEntity:
    external_id: str
    name: str
    canonical_name: str
    node_type: str
    confidence: float = 1.0
    aliases: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProvidedRelationship:
    source_external_id: str
    target_external_id: str
    edge_type: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class EntityProvider(Protocol):
    def entities(self, context: GraphBuildContext) -> list[ProvidedEntity]: ...


class RelationshipProvider(Protocol):
    def relationships(
        self, context: GraphBuildContext
    ) -> list[ProvidedRelationship]: ...

