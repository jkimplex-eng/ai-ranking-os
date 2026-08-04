from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.database import Base
from decision_center.models import ExecutionLog
from graph.models import GraphSnapshot
from maintenance.retention import RetentionPolicy, RetentionService


def test_retention_preserves_minimum_graph_snapshots_and_prunes_logs() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine) as db:
        for index in range(4):
            db.add(
                GraphSnapshot(
                    structure_version="1.0",
                    node_count=0,
                    edge_count=0,
                    build_metadata={},
                    created_at=now - timedelta(days=200 + index),
                )
            )
        db.add(
            ExecutionLog(
                entity_type="task",
                entity_id=1,
                action="old",
                changes={},
                created_at=now - timedelta(days=400),
            )
        )
        db.commit()
        result = RetentionService(
            db,
            RetentionPolicy(graph_snapshot_days=180, graph_min_snapshots=2),
        ).prune(now=now)
        assert result["graph_snapshots"] == 2
        assert result["execution_logs"] == 1
        assert db.query(GraphSnapshot).count() == 2
    engine.dispose()
