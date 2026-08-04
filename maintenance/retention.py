from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from decision_center.models import ExecutionLog
from execution_engine.models import Execution, ExecutionState
from graph.models import GraphSnapshot
from query_executor.models import QueryExecutionHistory


@dataclass(frozen=True)
class RetentionPolicy:
    graph_snapshot_days: int = 180
    graph_min_snapshots: int = 10
    execution_history_days: int = 90
    execution_log_days: int = 365


class RetentionService:
    """Bound operational history while preserving recent and active records."""

    def __init__(self, db: Session, policy: RetentionPolicy | None = None) -> None:
        self.db = db
        self.policy = policy or RetentionPolicy()

    def prune(self, *, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.now(UTC)
        keep_snapshots = (
            select(GraphSnapshot.id)
            .order_by(GraphSnapshot.id.desc())
            .limit(self.policy.graph_min_snapshots)
        )
        snapshots = self.db.execute(
            delete(GraphSnapshot).where(
                GraphSnapshot.created_at < now - timedelta(days=self.policy.graph_snapshot_days),
                GraphSnapshot.id.not_in(keep_snapshots),
            )
        ).rowcount
        query_history = self.db.execute(
            delete(QueryExecutionHistory).where(
                QueryExecutionHistory.created_at
                < now - timedelta(days=self.policy.execution_history_days)
            )
        ).rowcount
        executions = self.db.execute(
            delete(Execution).where(
                Execution.state.in_(
                    [
                        ExecutionState.COMPLETED,
                        ExecutionState.FAILED,
                        ExecutionState.CANCELLED,
                    ]
                ),
                Execution.finished_at < now - timedelta(days=self.policy.execution_history_days),
            )
        ).rowcount
        logs = self.db.execute(
            delete(ExecutionLog).where(
                ExecutionLog.created_at < now - timedelta(days=self.policy.execution_log_days)
            )
        ).rowcount
        self.db.commit()
        return {
            "graph_snapshots": snapshots,
            "query_execution_history": query_history,
            "executions": executions,
            "execution_logs": logs,
        }
