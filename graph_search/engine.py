from collections import deque

from graph_search.ports import GraphProvider, SearchEdge, SearchGraph, SearchNode
from graph_search.schemas import (
    GraphNeighborsResult,
    GraphSearchEdgeRead,
    GraphSearchNodeRead,
    GraphSearchResult,
    NeighborRead,
    TraversalDirection,
)


class GraphNodeNotFoundError(LookupError):
    """Requested node does not exist in the latest graph snapshot."""


class GraphSearchEngine:
    def __init__(self, graph_provider: GraphProvider) -> None:
        self.graph_provider = graph_provider

    def search(
        self,
        *,
        query: str | None = None,
        node_types: set[str] | None = None,
        relationship_types: set[str] | None = None,
        min_confidence: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> GraphSearchResult:
        graph = self.graph_provider.latest_graph()
        relationships = self._filter_edges(graph.edges, relationship_types, min_confidence)
        related_ids = {
            entity_id
            for edge in relationships
            for entity_id in (edge.source_entity_id, edge.target_entity_id)
        }
        normalized_query = self._normalize(query) if query else None
        normalized_types = {value.casefold() for value in node_types or set()}
        items = [
            node
            for node in graph.nodes
            if node.confidence >= min_confidence
            and (not normalized_types or node.node_type.casefold() in normalized_types)
            and (not relationship_types or node.entity_id in related_ids)
            and (not normalized_query or self._matches(node, normalized_query))
        ]
        items.sort(key=lambda node: (node.canonical_name.casefold(), node.entity_id))
        page_items = self._page(items, page, page_size)
        page_ids = {node.entity_id for node in page_items}
        result_edges = [
            edge
            for edge in relationships
            if edge.source_entity_id in page_ids or edge.target_entity_id in page_ids
        ]
        return GraphSearchResult(
            snapshot_id=graph.snapshot_id,
            query=query,
            page=page,
            page_size=page_size,
            total=len(items),
            items=[self._node_read(node) for node in page_items],
            relationships=[self._edge_read(edge) for edge in result_edges],
        )

    def get_node(self, entity_id: str) -> GraphSearchNodeRead:
        graph = self.graph_provider.latest_graph()
        return self._node_read(self._find_node(graph, entity_id))

    def neighbors(
        self,
        entity_id: str,
        *,
        depth: int = 1,
        direction: TraversalDirection = TraversalDirection.BOTH,
        node_types: set[str] | None = None,
        relationship_types: set[str] | None = None,
        min_confidence: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> GraphNeighborsResult:
        graph = self.graph_provider.latest_graph()
        root = self._find_node(graph, entity_id)
        nodes = {node.entity_id: node for node in graph.nodes}
        edges = self._filter_edges(graph.edges, relationship_types, min_confidence)
        adjacency: dict[str, list[tuple[str, SearchEdge]]] = {key: [] for key in nodes}
        for edge in edges:
            if direction in {TraversalDirection.OUTGOING, TraversalDirection.BOTH}:
                adjacency[edge.source_entity_id].append((edge.target_entity_id, edge))
            if direction in {TraversalDirection.INCOMING, TraversalDirection.BOTH}:
                adjacency[edge.target_entity_id].append((edge.source_entity_id, edge))
        visited = {entity_id: 0}
        traversed: dict[int, SearchEdge] = {}
        queue = deque([entity_id])
        while queue:
            current = queue.popleft()
            current_depth = visited[current]
            if current_depth >= depth:
                continue
            for neighbor_id, edge in sorted(
                adjacency.get(current, []), key=lambda item: (item[0], item[1].edge_id)
            ):
                if neighbor_id not in nodes:
                    continue
                traversed[edge.edge_id] = edge
                if neighbor_id not in visited:
                    visited[neighbor_id] = current_depth + 1
                    queue.append(neighbor_id)
        normalized_types = {value.casefold() for value in node_types or set()}
        found = [
            NeighborRead(depth=node_depth, node=self._node_read(nodes[node_id]))
            for node_id, node_depth in visited.items()
            if node_id != entity_id
            and nodes[node_id].confidence >= min_confidence
            and (not normalized_types or nodes[node_id].node_type.casefold() in normalized_types)
        ]
        found.sort(
            key=lambda item: (item.depth, item.node.canonical_name.casefold(), item.node.entity_id)
        )
        return GraphNeighborsResult(
            snapshot_id=graph.snapshot_id,
            root=self._node_read(root),
            direction=direction,
            max_depth=depth,
            page=page,
            page_size=page_size,
            total=len(found),
            items=self._page(found, page, page_size),
            traversed_relationships=[
                self._edge_read(edge)
                for edge in sorted(traversed.values(), key=lambda item: item.edge_id)
            ],
        )

    @staticmethod
    def _find_node(graph: SearchGraph, entity_id: str) -> SearchNode:
        for node in graph.nodes:
            if node.entity_id == entity_id or str(node.internal_id) == entity_id:
                return node
        raise GraphNodeNotFoundError(f"Graph node {entity_id!r} not found")

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())

    def _matches(self, node: SearchNode, query: str) -> bool:
        values = (node.entity_id, node.name, node.canonical_name, *node.aliases)
        return any(query in self._normalize(value) for value in values)

    @staticmethod
    def _filter_edges(
        edges: tuple[SearchEdge, ...],
        relationship_types: set[str] | None,
        min_confidence: float,
    ) -> list[SearchEdge]:
        normalized = {value.casefold() for value in relationship_types or set()}
        return [
            edge
            for edge in edges
            if edge.confidence >= min_confidence
            and (not normalized or edge.relationship_type.casefold() in normalized)
        ]

    @staticmethod
    def _page(items, page: int, page_size: int):
        start = (page - 1) * page_size
        return items[start : start + page_size]

    @staticmethod
    def _node_read(node: SearchNode) -> GraphSearchNodeRead:
        return GraphSearchNodeRead(
            internal_id=node.internal_id,
            entity_id=node.entity_id,
            name=node.name,
            canonical_name=node.canonical_name,
            node_type=node.node_type,
            confidence=node.confidence,
            aliases=list(node.aliases),
            properties=node.properties,
        )

    @staticmethod
    def _edge_read(edge: SearchEdge) -> GraphSearchEdgeRead:
        return GraphSearchEdgeRead(
            edge_id=edge.edge_id,
            source_entity_id=edge.source_entity_id,
            target_entity_id=edge.target_entity_id,
            relationship_type=edge.relationship_type,
            confidence=edge.confidence,
            properties=edge.properties,
        )
