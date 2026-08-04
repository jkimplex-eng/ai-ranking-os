from sqlalchemy.orm import Session

from entity_linking.engine import EntityLinkingEngine
from entity_linking.ports import GraphProvider, LinkableEntity, LinkableGraph
from entity_linking.resolver import NameEntityResolver
from graph.extraction_adapter import build_graph_engine


class PublicGraphAdapter(GraphProvider):
    """Adapter consuming only Graph Engine's public read contract."""

    def __init__(self, db: Session) -> None:
        self.graph_engine = build_graph_engine(db)

    def graph(self, snapshot_id: int | None = None) -> LinkableGraph:
        snapshot = (
            self.graph_engine.get(snapshot_id)
            if snapshot_id is not None
            else self.graph_engine.latest()
        )
        return LinkableGraph(
            snapshot_id=snapshot.id,
            entities=tuple(
                LinkableEntity(
                    graph_node_id=node.id,
                    external_id=node.external_id,
                    name=node.name,
                    canonical_name=node.canonical_name,
                    entity_type=node.node_type,
                    aliases=tuple(node.aliases),
                )
                for node in snapshot.nodes
            ),
        )


def build_entity_linking_engine(db: Session) -> EntityLinkingEngine:
    return EntityLinkingEngine(db, PublicGraphAdapter(db), NameEntityResolver())
