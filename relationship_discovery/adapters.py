from sqlalchemy.orm import Session

from graph.engine import GraphEngine
from graph.extraction_adapter import ExtractionGraphProvider, build_graph_engine
from graph.ports import GraphBuildContext, ProvidedRelationship
from relationship_discovery.engine import RelationshipDiscoveryEngine
from relationship_discovery.ports import (
    DiscoveryEntity,
    DiscoveryGraph,
    EvidenceItem,
    EvidenceProvider,
    ExistingRelationship,
    GraphProvider,
)


class PublicGraphAdapter(GraphProvider):
    def __init__(self, graph_engine: GraphEngine) -> None:
        self.graph_engine = graph_engine

    def graph(self, snapshot_id: int | None = None) -> DiscoveryGraph:
        snapshot = (
            self.graph_engine.get(snapshot_id)
            if snapshot_id is not None
            else self.graph_engine.latest()
        )
        external_by_node = {node.id: node.external_id for node in snapshot.nodes}
        return DiscoveryGraph(
            snapshot_id=snapshot.id,
            entities=tuple(DiscoveryEntity(node.external_id) for node in snapshot.nodes),
            relationships=tuple(
                ExistingRelationship(
                    external_by_node[edge.source_node_id],
                    external_by_node[edge.target_node_id],
                    edge.edge_type,
                )
                for edge in snapshot.edges
            ),
        )

    def integrate(self, snapshot_id: int, evidence: EvidenceItem) -> int:
        snapshot = self.graph_engine.derive(
            snapshot_id,
            [
                ProvidedRelationship(
                    source_external_id=evidence.source_external_id,
                    target_external_id=evidence.target_external_id,
                    edge_type=evidence.relationship_type,
                    confidence=evidence.confidence,
                    metadata=evidence.payload,
                )
            ],
        )
        return snapshot.id


class ExtractionEvidenceProvider(EvidenceProvider):
    TYPE_MAP = {
        "MENTIONS": "MENTIONS",
        "RECOMMENDS": "RECOMMENDS",
        "CITES": "REFERENCES",
        "REFERENCES": "REFERENCES",
        "COMPETES_WITH": "COMPETES_WITH",
        "RELATED_TO": "RELATED_TO",
        "PART_OF": "BELONGS_TO",
        "BELONGS_TO": "BELONGS_TO",
        "PRODUCES": "PRODUCES",
        "CREATED_BY": "CREATED_BY",
    }

    def __init__(self, provider: ExtractionGraphProvider) -> None:
        self.provider = provider

    def evidence(self, graph: DiscoveryGraph) -> list[EvidenceItem]:
        items = []
        for relationship in self.provider.relationships(GraphBuildContext()):
            mapped = self.TYPE_MAP.get(relationship.edge_type)
            if mapped is None:
                continue
            items.append(
                EvidenceItem(
                    source_external_id=relationship.source_external_id,
                    target_external_id=relationship.target_external_id,
                    relationship_type=mapped,
                    confidence=relationship.confidence,
                    source_type="entity_extraction",
                    source_reference=str(relationship.metadata.get("relation_id", "unknown")),
                    payload=relationship.metadata,
                )
            )
        return items


def build_relationship_discovery_engine(db: Session) -> RelationshipDiscoveryEngine:
    graph_engine = build_graph_engine(db)
    return RelationshipDiscoveryEngine(
        db,
        PublicGraphAdapter(graph_engine),
        ExtractionEvidenceProvider(ExtractionGraphProvider(db)),
    )
