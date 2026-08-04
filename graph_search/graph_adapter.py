from sqlalchemy.orm import Session

from graph.extraction_adapter import build_graph_engine
from graph_search.ports import GraphProvider, SearchEdge, SearchGraph, SearchNode


class PublicGraphSearchAdapter(GraphProvider):
    """Adapts Graph Engine's public snapshot DTO to the search port."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def latest_graph(self) -> SearchGraph:
        graph = build_graph_engine(self.db).latest()
        entity_ids = {node.id: node.external_id for node in graph.nodes}
        return SearchGraph(
            snapshot_id=graph.id,
            nodes=tuple(
                SearchNode(
                    internal_id=node.id,
                    entity_id=node.external_id,
                    name=node.name,
                    canonical_name=node.canonical_name,
                    node_type=node.node_type,
                    confidence=node.confidence,
                    aliases=tuple(node.aliases),
                    properties=node.properties,
                )
                for node in graph.nodes
            ),
            edges=tuple(
                SearchEdge(
                    edge_id=edge.id,
                    source_entity_id=entity_ids[edge.source_node_id],
                    target_entity_id=entity_ids[edge.target_node_id],
                    relationship_type=edge.edge_type,
                    confidence=edge.confidence,
                    properties=edge.properties,
                )
                for edge in graph.edges
                if edge.source_node_id in entity_ids and edge.target_node_id in entity_ids
            ),
        )
