from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from decision_center.models import Task, TaskStatus
from execution_engine.models import Execution, ExecutionState
from execution_engine.service import recover_stale_executions
from research.models import (
    Research,
    ResearchJob,
    ResearchJobState,
    ResearchStatus,
    ResearchTask,
    ResearchTaskStatus,
)
from research.queue import STALE_RESEARCH_ERROR, recover_stale_researches


def test_worker_recovery_marks_abandoned_research_and_execution_terminal() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    stale_at = datetime.now(UTC) - timedelta(minutes=30)

    with session_factory() as db:
        research = Research(title="Interrupted research", status=ResearchStatus.ACTIVE)
        decision_task = Task(title="Interrupted task", status=TaskStatus.IN_PROGRESS)
        db.add_all([research, decision_task])
        db.flush()
        research_task = ResearchTask(
            research_id=research.id,
            query="Which brand is recommended?",
            status=ResearchTaskStatus.RUNNING,
            decision_task_id=decision_task.id,
        )
        pending_decision_task = Task(title="Queued follow-up", status=TaskStatus.READY)
        db.add(pending_decision_task)
        db.flush()
        pending_research_task = ResearchTask(
            research_id=research.id,
            query="Which source should be checked?",
            status=ResearchTaskStatus.PENDING,
            decision_task_id=pending_decision_task.id,
        )
        execution = Execution(
            task_id=decision_task.id,
            state=ExecutionState.RUNNING,
            started_at=stale_at,
        )
        job = ResearchJob(
            research_id=research.id,
            state=ResearchJobState.RUNNING,
            started_at=stale_at,
            payload={},
        )
        db.add_all([research_task, pending_research_task, execution, job])
        db.commit()

        research.updated_at = stale_at
        research_task.updated_at = stale_at
        pending_research_task.updated_at = stale_at
        db.commit()

        assert recover_stale_executions(db, stale_after_seconds=60) == 1
        assert recover_stale_researches(db, stale_after_seconds=60) == [research.id]

        db.refresh(research)
        db.refresh(research_task)
        db.refresh(execution)
        db.refresh(decision_task)
        db.refresh(pending_decision_task)
        db.refresh(job)
        assert research.status == ResearchStatus.FAILED
        assert research.progress_percent == 100
        assert research.failed_tasks == 2
        assert research_task.status == ResearchTaskStatus.FAILED
        assert research_task.error == STALE_RESEARCH_ERROR
        assert job.state == ResearchJobState.FAILED
        assert job.error == STALE_RESEARCH_ERROR
        assert execution.state == ExecutionState.FAILED
        assert decision_task.status == TaskStatus.BLOCKED
        assert pending_decision_task.status == TaskStatus.BLOCKED

    Base.metadata.drop_all(engine)


def test_recovery_keeps_recent_active_research_running() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as db:
        research = Research(title="Current research", status=ResearchStatus.ACTIVE)
        db.add(research)
        db.flush()
        db.add(
            ResearchJob(
                research_id=research.id,
                state=ResearchJobState.RUNNING,
                started_at=datetime.now(UTC),
                payload={},
            )
        )
        db.commit()

        assert recover_stale_researches(db, stale_after_seconds=60) == []
        db.refresh(research)
        assert research.status == ResearchStatus.ACTIVE

    Base.metadata.drop_all(engine)
