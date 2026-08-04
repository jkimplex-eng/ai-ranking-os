from sqlalchemy import select
from sqlalchemy.orm import Session

from entity_extraction.models import EntityHistory, RelationHistory
from graph.engine import GraphEngine
from graph.ports import (
    EntityProvider,
    GraphBuildContext,
    ProvidedEntity,
    ProvidedRelationship,
    RelationshipProvider,
)


class ExtractionGraphProvider(EntityProvider, RelationshipProvider):
    """Infrastructure adapter for persisted Entity Extraction output."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def entities(self, context: GraphBuildContext) -> list[ProvidedEntity]:
        statement = select(EntityHistory)
        if context.source_ids:
            statement = statement.where(EntityHistory.response_id.in_(context.source_ids))
        rows = self.db.scalars(statement.order_by(EntityHistory.id)).all()
        return [
            ProvidedEntity(
                external_id=self._external_id(row),
                name=row.name,
                canonical_name=row.canonical_name,
                node_type=self._node_type(row.entity_type),
                confidence=row.confidence,
                aliases=tuple(row.aliases),
                metadata={
                    "response_id": row.response_id,
                    "knowledge_graph_id": row.knowledge_graph_id,
                },
            )
            for row in rows
        ]

    def relationships(self, context: GraphBuildContext) -> list[ProvidedRelationship]:
        entity_statement = select(EntityHistory)
        relation_statement = select(RelationHistory)
        if context.source_ids:
            entity_statement = entity_statement.where(
                EntityHistory.response_id.in_(context.source_ids)
            )
            relation_statement = relation_statement.where(
                RelationHistory.response_id.in_(context.source_ids)
            )
        entities = self.db.scalars(entity_statement).all()
        external_ids = {
            (entity.run_id, entity.entity_id): self._external_id(entity)
            for entity in entities
        }
        relationships = []
        for relation in self.db.scalars(relation_statement.order_by(RelationHistory.id)):
            source = external_ids.get((relation.run_id, relation.source_entity_id))
            target = external_ids.get((relation.run_id, relation.target_entity_id))
            if source is None or target is None:
                continue
            relationships.append(
                ProvidedRelationship(
                    source_external_id=source,
                    target_external_id=target,
                    edge_type=relation.relation_type,
                    confidence=relation.confidence,
                    metadata={
                        "response_id": relation.response_id,
                        "relation_id": relation.relation_id,
                    },
                )
            )
        return relationships

    @staticmethod
    def _external_id(entity: EntityHistory) -> str:
        return entity.knowledge_graph_id or f"{entity.response_id}:{entity.entity_id}"

    @staticmethod
    def _node_type(value: str) -> str:
        return value.replace("_", " ").title().replace(" ", "")


def build_graph_engine(db: Session) -> GraphEngine:
    provider = ExtractionGraphProvider(db)
    return GraphEngine(db, provider, provider)
