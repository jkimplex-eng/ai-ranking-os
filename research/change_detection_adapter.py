from sqlalchemy import select
from sqlalchemy.orm import Session

from change_detection.ports import ChangeSnapshot
from graph.engine import GraphEngine
from graph.models import GraphSnapshot
from research.models import Research, ResearchStatus
from research.reporting import ReportingService


class ResearchChangeSnapshotSource:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _snapshot(self, research: Research) -> ChangeSnapshot:
        report = ReportingService(self.db).get_report(research.id).model_dump(mode="json")
        score = report.get("score") or {}
        graph_rows = list(
            self.db.scalars(
                select(GraphSnapshot).order_by(
                    GraphSnapshot.created_at.desc(), GraphSnapshot.id.desc()
                )
            )
        )
        graph_row = next(
            (
                item
                for item in graph_rows
                if item.build_metadata.get("research_id") == research.id
            ),
            None,
        )
        graph_nodes: frozenset[str] = frozenset()
        graph_edges: frozenset[str] = frozenset()
        if graph_row is not None:
            graph = GraphEngine(self.db, None, None).get(graph_row.id)
            node_names = {node.id: node.external_id for node in graph.nodes}
            graph_nodes = frozenset(node.external_id for node in graph.nodes)
            graph_edges = frozenset(
                f"{node_names[edge.source_node_id]}:{edge.edge_type}:{node_names[edge.target_node_id]}"
                for edge in graph.edges
            )
        sources = frozenset(
            str(item.get("url") or item.get("source") or item.get("title"))
            for item in report.get("citations", [])
            if item.get("url") or item.get("source") or item.get("title")
        )
        return ChangeSnapshot(
            research_id=research.id,
            metrics={
                key: float(value)
                for key, value in score.items()
                if key.endswith("_score") and isinstance(value, int | float)
            },
            recommendations=frozenset(
                item["content"]
                for item in report.get("recommendations", [])
                if item.get("content")
            ),
            sources=sources,
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
        )

    def pair(self, research_id: int) -> tuple[ChangeSnapshot | None, ChangeSnapshot]:
        current = self.db.get(Research, research_id)
        if current is None:
            raise LookupError(f"Research {research_id} not found")
        statement = select(Research).where(
            Research.id != current.id,
            Research.created_at <= current.created_at,
            Research.status == ResearchStatus.COMPLETED,
        )
        if current.project_id is not None:
            statement = statement.where(Research.project_id == current.project_id)
        elif current.entity_id is not None:
            statement = statement.where(Research.entity_id == current.entity_id)
        previous = self.db.scalar(
            statement.order_by(Research.created_at.desc(), Research.id.desc())
        )
        return (
            self._snapshot(previous) if previous is not None else None,
            self._snapshot(current),
        )
