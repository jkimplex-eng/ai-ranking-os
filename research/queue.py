from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from research.models import Research, ResearchJob, ResearchJobState, ResearchStatus
from research.repositories import EntityNotFoundError
from research.schemas import ResearchEnqueueRequest, ResearchJobRead, ResearchRunRequest
from research.service import run_research


class ResearchAlreadyQueuedError(RuntimeError):
    pass


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
