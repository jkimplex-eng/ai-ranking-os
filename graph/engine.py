from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from graph.models import GraphEdge, GraphNode, GraphSnapshot
from graph.ports import (
    EntityProvider,
    GraphBuildContext,
    ProvidedEntity,
    ProvidedRelationship,
    RelationshipProvider,
)
from graph.schemas import GraphEdgeRead, GraphNodeRead, GraphSnapshotRead


class GraphSnapshotNotFoundError(LookupError):
    """Requested graph snapshot does not exist."""


class GraphEngine:
    STRUCTURE_VERSION = "1.0"

    def __init__(
        self,
        db: Session,
        entity_provider: EntityProvider,
        relationship_provider: RelationshipProvider,
    ) -> None:
        self.db = db
        self.entity_provider = entity_provider
        self.relationship_provider = relationship_provider

    def build(self, context: GraphBuildContext) -> GraphSnapshotRead:
        entities = self._deduplicate_entities(self.entity_provider.entities(context))
        relationships = self.relationship_provider.relationships(context)
        snapshot = GraphSnapshot(
            structure_version=self.STRUCTURE_VERSION,
            node_count=len(entities),
            edge_count=0,
            build_metadata={**context.metadata, "source_ids": list(context.source_ids)},
        )
        self.db.add(snapshot)
        self.db.flush()
        nodes: dict[str, GraphNode] = {}
        for entity in entities.values():
            node = GraphNode(
                snapshot_id=snapshot.id,
                external_id=entity.external_id,
                name=entity.name,
                canonical_name=entity.canonical_name,
                node_type=entity.node_type,
                confidence=entity.confidence,
                aliases=list(entity.aliases),
                properties=entity.metadata,
            )
            self.db.add(node)
            self.db.flush()
            nodes[entity.external_id] = node
        unique_edges = {}
        for relationship in relationships:
            source = nodes.get(relationship.source_external_id)
            target = nodes.get(relationship.target_external_id)
            if source is None or target is None:
                continue
            key = (source.id, target.id, relationship.edge_type)
            current = unique_edges.get(key)
            if current is None or relationship.confidence > current.confidence:
                unique_edges[key] = relationship
        for (source_id, target_id, edge_type), relationship in unique_edges.items():
            self.db.add(
                GraphEdge(
                    snapshot_id=snapshot.id,
                    source_node_id=source_id,
                    target_node_id=target_id,
                    edge_type=edge_type,
                    confidence=relationship.confidence,
                    properties=relationship.metadata,
                )
            )
        snapshot.edge_count = len(unique_edges)
        self.db.commit()
        return self.get(snapshot.id)

    def latest(self) -> GraphSnapshotRead:
        snapshot_id = self.db.scalar(
            select(GraphSnapshot.id).order_by(
                GraphSnapshot.created_at.desc(), GraphSnapshot.id.desc()
            )
        )
        if snapshot_id is None:
            raise GraphSnapshotNotFoundError("No graph snapshots exist")
        return self.get(snapshot_id)

    def get(self, snapshot_id: int) -> GraphSnapshotRead:
        snapshot = self.db.scalar(
            select(GraphSnapshot)
            .options(selectinload(GraphSnapshot.nodes), selectinload(GraphSnapshot.edges))
            .where(GraphSnapshot.id == snapshot_id)
        )
        if snapshot is None:
            raise GraphSnapshotNotFoundError(f"Graph snapshot {snapshot_id} not found")
        return self._read(snapshot)

    def derive(
        self,
        snapshot_id: int,
        relationships: list[ProvidedRelationship],
    ) -> GraphSnapshotRead:
        """Create an immutable snapshot by adding relationships to an existing graph."""

        base = self.get(snapshot_id)
        snapshot = GraphSnapshot(
            structure_version=self.STRUCTURE_VERSION,
            node_count=base.node_count,
            edge_count=0,
            build_metadata={"derived_from_snapshot_id": snapshot_id},
        )
        self.db.add(snapshot)
        self.db.flush()
        old_to_new: dict[int, GraphNode] = {}
        external_to_new: dict[str, GraphNode] = {}
        for item in base.nodes:
            node = GraphNode(
                snapshot_id=snapshot.id,
                external_id=item.external_id,
                name=item.name,
                canonical_name=item.canonical_name,
                node_type=item.node_type,
                confidence=item.confidence,
                aliases=item.aliases,
                properties=item.properties,
            )
            self.db.add(node)
            self.db.flush()
            old_to_new[item.id] = node
            external_to_new[item.external_id] = node
        edge_keys: set[tuple[int, int, str]] = set()
        for item in base.edges:
            source = old_to_new[item.source_node_id]
            target = old_to_new[item.target_node_id]
            edge_keys.add((source.id, target.id, item.edge_type))
            self.db.add(
                GraphEdge(
                    snapshot_id=snapshot.id,
                    source_node_id=source.id,
                    target_node_id=target.id,
                    edge_type=item.edge_type,
                    confidence=item.confidence,
                    properties=item.properties,
                )
            )
        for item in relationships:
            source = external_to_new.get(item.source_external_id)
            target = external_to_new.get(item.target_external_id)
            if source is None or target is None:
                continue
            key = (source.id, target.id, item.edge_type)
            if key in edge_keys:
                continue
            edge_keys.add(key)
            self.db.add(
                GraphEdge(
                    snapshot_id=snapshot.id,
                    source_node_id=source.id,
                    target_node_id=target.id,
                    edge_type=item.edge_type,
                    confidence=item.confidence,
                    properties=item.metadata,
                )
            )
        snapshot.edge_count = len(edge_keys)
        self.db.commit()
        return self.get(snapshot.id)

    @staticmethod
    def _deduplicate_entities(entities: list[ProvidedEntity]) -> dict[str, ProvidedEntity]:
        result: dict[str, ProvidedEntity] = {}
        for entity in entities:
            current = result.get(entity.external_id)
            if current is None or entity.confidence > current.confidence:
                result[entity.external_id] = entity
        return result

    @staticmethod
    def _read(snapshot: GraphSnapshot) -> GraphSnapshotRead:
        return GraphSnapshotRead(
            id=snapshot.id,
            structure_version=snapshot.structure_version,
            node_count=snapshot.node_count,
            edge_count=snapshot.edge_count,
            build_metadata=snapshot.build_metadata,
            created_at=snapshot.created_at,
            nodes=[
                GraphNodeRead(
                    id=node.id,
                    external_id=node.external_id,
                    name=node.name,
                    canonical_name=node.canonical_name,
                    node_type=node.node_type,
                    confidence=node.confidence,
                    aliases=node.aliases,
                    properties=node.properties,
                )
                for node in sorted(snapshot.nodes, key=lambda item: item.id)
            ],
            edges=[
                GraphEdgeRead(
                    id=edge.id,
                    source_node_id=edge.source_node_id,
                    target_node_id=edge.target_node_id,
                    edge_type=edge.edge_type,
                    confidence=edge.confidence,
                    properties=edge.properties,
                )
                for edge in sorted(snapshot.edges, key=lambda item: item.id)
            ],
        )
