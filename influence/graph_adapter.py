from sqlalchemy.orm import Session

from graph.extraction_adapter import build_graph_engine
from influence.ports import GraphProvider, InfluenceEdge, InfluenceGraph, InfluenceNode


class PublicGraphAdapter(GraphProvider):
    """Maps the Graph Engine public DTO into the influence read port."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def latest_graph(self) -> InfluenceGraph:
        graph = build_graph_engine(self.db).latest()
        external_ids = {node.id: node.external_id for node in graph.nodes}
        return InfluenceGraph(
            snapshot_id=graph.id,
            nodes=tuple(
                InfluenceNode(node.external_id, node.name, node.node_type) for node in graph.nodes
            ),
            edges=tuple(
                InfluenceEdge(
                    external_ids[edge.source_node_id],
                    external_ids[edge.target_node_id],
                    edge.confidence,
                )
                for edge in graph.edges
                if edge.source_node_id in external_ids and edge.target_node_id in external_ids
            ),
        )
