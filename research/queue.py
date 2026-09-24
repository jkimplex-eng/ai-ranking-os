from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from decision_center.models import Task, TaskStatus
from research.models import (
    Research,
    ResearchJob,
    ResearchJobState,
    ResearchStatus,
    ResearchTask,
    ResearchTaskStatus,
)
from research.repositories import EntityNotFoundError
from research.schemas import ResearchEnqueueRequest, ResearchJobRead, ResearchRunRequest
from research.service import run_research


class ResearchAlreadyQueuedError(RuntimeError):
    pass


STALE_RESEARCH_ERROR = "Research expired after worker interruption"


def get_job(db: Session, job_id: int) -> ResearchJobRead:
    job = db.get(ResearchJob, job_id)
    if job is None:
        raise EntityNotFoundError(f"Research job {job_id} not found")
    return ResearchJobRead.model_validate(job)


def enqueue(db: Session, payload: ResearchEnqueueRequest) -> ResearchJobRead:
    research = db.get(Research, payload.research_id)
    if research is None:
        raise EntityNotFoundError(f"Research {payload.research_id} not found")
    active = db.scalar(
        select(ResearchJob).where(
            ResearchJob.research_id == payload.research_id,
            ResearchJob.state.in_([ResearchJobState.PENDING, ResearchJobState.RUNNING]),
        )
    )
    if active is not None:
        raise ResearchAlreadyQueuedError(f"Research {payload.research_id} is already queued")
    research.status = ResearchStatus.ACTIVE
    job = ResearchJob(
        research_id=payload.research_id,
        state=ResearchJobState.PENDING,
        payload=payload.model_dump(mode="json", exclude={"research_id"}),
        attempts=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return ResearchJobRead.model_validate(job)


def process_next(db: Session) -> ResearchJob | None:
    job = db.scalar(
        select(ResearchJob)
        .where(ResearchJob.state == ResearchJobState.PENDING)
        .order_by(ResearchJob.created_at, ResearchJob.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        return None
    job.state = ResearchJobState.RUNNING
    job.attempts += 1
    job.started_at = datetime.now(UTC)
    db.commit()
    try:
        research = run_research(
            db,
            job.research_id,
            ResearchRunRequest.model_validate(job.payload),
            allow_active=True,
        )
        if research.status == ResearchStatus.FAILED:
            job.state = ResearchJobState.FAILED
            job.error = "Research execution completed with failed tasks"
        else:
            job.state = ResearchJobState.COMPLETED
    except Exception as error:
        job.state = ResearchJobState.FAILED
        job.error = str(error)
        research = db.get(Research, job.research_id)
        if research is not None:
            research.status = ResearchStatus.FAILED
    job.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job


def recover_stale_researches(
    db: Session,
    *,
    stale_after_seconds: int | None = None,
) -> list[int]:
    """Terminally mark abandoned research so clients never see week-old runs as active."""
    timeout = stale_after_seconds or get_settings().research_stale_seconds
    cutoff = datetime.now(UTC) - timedelta(seconds=timeout)
    recovered: list[int] = []
    active_researches = list(
        db.scalars(
            select(Research).where(
                Research.status == ResearchStatus.ACTIVE,
                Research.updated_at < cutoff,
            )
        )
    )
    for research in active_researches:
        active_job = db.scalar(
            select(ResearchJob)
            .where(
                ResearchJob.research_id == research.id,
                ResearchJob.state.in_([ResearchJobState.PENDING, ResearchJobState.RUNNING]),
            )
            .order_by(ResearchJob.id.desc())
            .limit(1)
        )
        job_activity = (
            (active_job.started_at or active_job.created_at) if active_job is not None else None
        )
        if job_activity is not None and job_activity >= cutoff:
            continue
        if active_job is not None:
            active_job.state = ResearchJobState.FAILED
            active_job.error = STALE_RESEARCH_ERROR
            active_job.finished_at = datetime.now(UTC)

        stale_tasks = list(
            db.scalars(
                select(ResearchTask).where(
                    ResearchTask.research_id == research.id,
                    ResearchTask.status.in_([
                        ResearchTaskStatus.PENDING,
                        ResearchTaskStatus.RUNNING,
                    ]),
                    ResearchTask.updated_at < cutoff,
                )
            )
        )
        for task in stale_tasks:
            task.status = ResearchTaskStatus.FAILED
            task.error = STALE_RESEARCH_ERROR
            if task.decision_task_id is not None:
                decision_task = db.get(Task, task.decision_task_id)
                if decision_task is not None and decision_task.status in {
                    TaskStatus.READY,
                    TaskStatus.IN_PROGRESS,
                }:
                    decision_task.status = TaskStatus.BLOCKED
                    decision_task.owner_id = None

        research.completed_tasks = int(
            db.scalar(
                select(func.count())
                .select_from(ResearchTask)
                .where(
                    ResearchTask.research_id == research.id,
                    ResearchTask.status == ResearchTaskStatus.COMPLETED,
                )
            )
            or 0
        )
        research.failed_tasks = int(
            db.scalar(
                select(func.count())
                .select_from(ResearchTask)
                .where(
                    ResearchTask.research_id == research.id,
                    ResearchTask.status == ResearchTaskStatus.FAILED,
                )
            )
            or 0
        )
        research.status = ResearchStatus.FAILED
        research.progress_percent = 100.0
        recovered.append(research.id)
    if recovered:
        db.commit()
    return recovered
