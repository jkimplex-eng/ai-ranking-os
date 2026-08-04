from collections import deque

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from influence.models import EntityInfluence, InfluenceSnapshot
from influence.ports import GraphProvider, InfluenceGraph
from influence.schemas import EntityInfluenceRead, InfluenceSnapshotRead


class EntityInfluenceNotFoundError(LookupError):
    """Requested entity does not occur in the latest graph."""


class InfluenceEngine:
    ALGORITHM_VERSION = "1.0"
    DAMPING = 0.85
    SCORE_WEIGHTS = {
        "degree": 0.20,
        "weighted_degree": 0.20,
        "pagerank": 0.25,
        "betweenness": 0.15,
        "closeness": 0.20,
    }

    def __init__(self, db: Session, graph_provider: GraphProvider) -> None:
        self.db = db
        self.graph_provider = graph_provider

    def calculate(self) -> InfluenceSnapshotRead:
        graph = self.graph_provider.latest_graph()
        existing = self.db.scalar(
            select(InfluenceSnapshot)
            .options(selectinload(InfluenceSnapshot.entities))
            .where(
                InfluenceSnapshot.graph_snapshot_id == graph.snapshot_id,
                InfluenceSnapshot.algorithm_version == self.ALGORITHM_VERSION,
            )
        )
        if existing is not None:
            return self._read(existing)

        metrics = self._metrics(graph)
        snapshot = InfluenceSnapshot(
            graph_snapshot_id=graph.snapshot_id,
            algorithm_version=self.ALGORITHM_VERSION,
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
        )
        self.db.add(snapshot)
        self.db.flush()
        ordered = sorted(metrics.items(), key=lambda item: (-item[1]["influence_score"], item[0]))
        nodes = {node.entity_id: node for node in graph.nodes}
        for rank, (entity_id, values) in enumerate(ordered, start=1):
            node = nodes[entity_id]
            self.db.add(
                EntityInfluence(
                    snapshot_id=snapshot.id,
                    entity_id=entity_id,
                    name=node.name,
                    node_type=node.node_type,
                    rank=rank,
                    **values,
                )
            )
        self.db.commit()
        return self._get(snapshot.id)

    def get_entity(self, entity_id: str) -> EntityInfluenceRead:
        snapshot = self.calculate()
        for entity in snapshot.entities:
            if entity.entity_id == entity_id:
                return entity
        raise EntityInfluenceNotFoundError(f"Entity {entity_id!r} not found in latest graph")

    def _metrics(self, graph: InfluenceGraph) -> dict[str, dict[str, float]]:
        ids = [node.entity_id for node in graph.nodes]
        node_set = set(ids)
        outgoing = {node_id: set() for node_id in ids}
        incoming = {node_id: set() for node_id in ids}
        weighted = dict.fromkeys(ids, 0.0)
        for edge in graph.edges:
            source, target = edge.source_entity_id, edge.target_entity_id
            if source not in node_set or target not in node_set or source == target:
                continue
            outgoing[source].add(target)
            incoming[target].add(source)
            weight = min(1.0, max(0.0, edge.weight))
            weighted[source] += weight
            weighted[target] += weight
        size = len(ids)
        denominator = max(1, size - 1)
        degree = {
            node_id: len(outgoing[node_id] | incoming[node_id]) / denominator if size > 1 else 0.0
            for node_id in ids
        }
        weighted_degree = {
            node_id: min(1.0, weighted[node_id] / (2 * denominator)) if size > 1 else 0.0
            for node_id in ids
        }
        pagerank = self._pagerank(ids, outgoing, incoming)
        betweenness = self._betweenness(ids, outgoing)
        closeness = self._closeness(ids, outgoing)
        max_pagerank = max(pagerank.values(), default=0.0)
        result = {}
        for node_id in ids:
            normalized_pagerank = pagerank[node_id] / max_pagerank if max_pagerank else 0.0
            score = 100 * (
                self.SCORE_WEIGHTS["degree"] * degree[node_id]
                + self.SCORE_WEIGHTS["weighted_degree"] * weighted_degree[node_id]
                + self.SCORE_WEIGHTS["pagerank"] * normalized_pagerank
                + self.SCORE_WEIGHTS["betweenness"] * betweenness[node_id]
                + self.SCORE_WEIGHTS["closeness"] * closeness[node_id]
            )
            result[node_id] = {
                "degree": round(degree[node_id], 6),
                "weighted_degree": round(weighted_degree[node_id], 6),
                "pagerank": round(pagerank[node_id], 6),
                "betweenness": round(betweenness[node_id], 6),
                "closeness": round(closeness[node_id], 6),
                "influence_score": round(min(100.0, score), 2),
            }
        return result

    def _pagerank(self, ids, outgoing, incoming) -> dict[str, float]:
        size = len(ids)
        if size == 0:
            return {}
        ranks = dict.fromkeys(ids, 1 / size)
        for _ in range(100):
            sink_share = sum(ranks[node] for node in ids if not outgoing[node]) / size
            updated = {}
            for node in ids:
                inbound = sum(ranks[parent] / len(outgoing[parent]) for parent in incoming[node])
                updated[node] = (1 - self.DAMPING) / size + self.DAMPING * (sink_share + inbound)
            if sum(abs(updated[node] - ranks[node]) for node in ids) < 1e-10:
                ranks = updated
                break
            ranks = updated
        return ranks

    @staticmethod
    def _betweenness(ids, outgoing) -> dict[str, float]:
        scores = dict.fromkeys(ids, 0.0)
        for source in ids:
            stack = []
            predecessors = {node: [] for node in ids}
            paths = dict.fromkeys(ids, 0.0)
            paths[source] = 1.0
            distance = dict.fromkeys(ids, -1)
            distance[source] = 0
            queue = deque([source])
            while queue:
                node = queue.popleft()
                stack.append(node)
                for target in outgoing[node]:
                    if distance[target] < 0:
                        queue.append(target)
                        distance[target] = distance[node] + 1
                    if distance[target] == distance[node] + 1:
                        paths[target] += paths[node]
                        predecessors[target].append(node)
            dependency = dict.fromkeys(ids, 0.0)
            while stack:
                target = stack.pop()
                for parent in predecessors[target]:
                    dependency[parent] += (paths[parent] / paths[target]) * (1 + dependency[target])
                if target != source:
                    scores[target] += dependency[target]
        size = len(ids)
        normalizer = (size - 1) * (size - 2)
        return {node: scores[node] / normalizer if normalizer > 0 else 0.0 for node in ids}

    @staticmethod
    def _closeness(ids, outgoing) -> dict[str, float]:
        size = len(ids)
        result = {}
        for source in ids:
            distances = {source: 0}
            queue = deque([source])
            while queue:
                node = queue.popleft()
                for target in outgoing[node]:
                    if target not in distances:
                        distances[target] = distances[node] + 1
                        queue.append(target)
            reachable = len(distances) - 1
            total = sum(distances.values())
            result[source] = (
                (reachable / total) * (reachable / (size - 1))
                if reachable and total and size > 1
                else 0.0
            )
        return result

    def _get(self, snapshot_id: int) -> InfluenceSnapshotRead:
        snapshot = self.db.scalar(
            select(InfluenceSnapshot)
            .options(selectinload(InfluenceSnapshot.entities))
            .where(InfluenceSnapshot.id == snapshot_id)
        )
        if snapshot is None:  # defensive: created in the same transaction
            raise RuntimeError("Persisted influence snapshot disappeared")
        return self._read(snapshot)

    @staticmethod
    def _read(snapshot: InfluenceSnapshot) -> InfluenceSnapshotRead:
        return InfluenceSnapshotRead(
            id=snapshot.id,
            graph_snapshot_id=snapshot.graph_snapshot_id,
            algorithm_version=snapshot.algorithm_version,
            node_count=snapshot.node_count,
            edge_count=snapshot.edge_count,
            calculated_at=snapshot.calculated_at,
            entities=[
                EntityInfluenceRead(
                    entity_id=item.entity_id,
                    name=item.name,
                    node_type=item.node_type,
                    degree=item.degree,
                    weighted_degree=item.weighted_degree,
                    pagerank=item.pagerank,
                    betweenness=item.betweenness,
                    closeness=item.closeness,
                    influence_score=item.influence_score,
                    rank=item.rank,
                )
                for item in sorted(snapshot.entities, key=lambda value: value.rank)
            ],
        )
