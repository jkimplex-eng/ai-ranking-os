from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi import Response as HTTPResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from research import service
from research.comparison import ComparisonNotReadyError, ComparisonService
from research.extraction import ExtractionProcessingError, ExtractionService
from research.history import ResearchHistoryService
from research.queue import ResearchAlreadyQueuedError, enqueue, get_job
from research.reporting import ReportingService
from research.repositories import (
    EntityNotFoundError,
    ResearchRepository,
    ResearchTaskRepository,
    ResponseRepository,
)
from research.schemas import (
    ExtractionResultRead,
    ResearchComparisonRead,
    ResearchCreate,
    ResearchEnqueueRequest,
    ResearchHistoryRead,
    ResearchJobRead,
    ResearchRead,
    ResearchReportRead,
    ResearchRunRequest,
    ResearchScoreRead,
    ResearchTaskCreate,
    ResearchTaskRead,
    ResearchTaskUpdate,
    ResearchUpdate,
    ResponseCreate,
    ResponseRead,
    ResponseUpdate,
)
from research.scoring import ScoringNotReadyError, ScoringService

router = APIRouter(tags=["research"])
DbSession = Annotated[Session, Depends(get_db)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


def _not_found(error: EntityNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


def _conflict(error: service.ResearchRunConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("/research", response_model=list[ResearchRead])
def list_research(
    db: DbSession,
    offset: Offset = 0,
    limit: Limit = 100,
) -> list[ResearchRead]:
    return ResearchRepository(db).list(offset=offset, limit=limit)


@router.post(
    "/research",
    response_model=ResearchRead,
    status_code=status.HTTP_201_CREATED,
)
def create_research_api(payload: ResearchCreate, db: DbSession) -> ResearchRead:
    return ResearchRepository(db).create(payload)


@router.get(
    "/research/history",
    response_model=ResearchHistoryRead,
)
def get_research_history(
    db: DbSession,
    entity_id: UUID,
    offset: Offset = 0,
    limit: Limit = 100,
) -> ResearchHistoryRead:
    return ResearchHistoryService(db).get_history(
        entity_id,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/research/compare",
    response_model=ResearchComparisonRead,
)
def compare_research(
    db: DbSession,
    left: int = Query(ge=1),
    right: int = Query(ge=1),
) -> ResearchComparisonRead:
    try:
        return ComparisonService(db).compare(left, right)
    except EntityNotFoundError as error:
        raise _not_found(error) from error
    except ComparisonNotReadyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post("/research/run", response_model=ResearchJobRead, status_code=status.HTTP_202_ACCEPTED)
def enqueue_research(payload: ResearchEnqueueRequest, db: DbSession) -> ResearchJobRead:
    try:
        return enqueue(db, payload)
    except EntityNotFoundError as error:
        raise _not_found(error) from error
    except ResearchAlreadyQueuedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/research/jobs/{job_id}", response_model=ResearchJobRead)
def get_research_job(job_id: int, db: DbSession) -> ResearchJobRead:
    try:
        return get_job(db, job_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.get("/research/{research_id}", response_model=ResearchRead)
def get_research_api(research_id: int, db: DbSession) -> ResearchRead:
    try:
        return ResearchRepository(db).get(research_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.patch("/research/{research_id}", response_model=ResearchRead)
def update_research_api(
    research_id: int,
    payload: ResearchUpdate,
    db: DbSession,
) -> ResearchRead:
    try:
        return ResearchRepository(db).update(research_id, payload)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.delete(
    "/research/{research_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_research_api(research_id: int, db: DbSession) -> HTTPResponse:
    try:
        ResearchRepository(db).delete(research_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error
    return HTTPResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/research/{research_id}/run", response_model=ResearchRead)
def run_research(
    research_id: int,
    payload: ResearchRunRequest,
    db: DbSession,
) -> ResearchRead:
    try:
        return service.run_research(db, research_id, payload)
    except EntityNotFoundError as error:
        raise _not_found(error) from error
    except service.ResearchRunConflictError as error:
        raise _conflict(error) from error


@router.post(
    "/research/{research_id}/score",
    response_model=ResearchScoreRead,
)
def calculate_research_score(
    research_id: int,
    db: DbSession,
) -> ResearchScoreRead:
    try:
        return ScoringService(db).calculate(research_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error
    except ScoringNotReadyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.get(
    "/research/{research_id}/score",
    response_model=ResearchScoreRead,
)
def get_research_score(
    research_id: int,
    db: DbSession,
) -> ResearchScoreRead:
    try:
        return ScoringService(db).get(research_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.get(
    "/research/{research_id}/report",
    response_model=ResearchReportRead,
)
def get_research_report(
    research_id: int,
    db: DbSession,
) -> ResearchReportRead:
    try:
        return ReportingService(db).get_report(research_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.get("/researches", response_model=list[ResearchRead])
def list_researches(
    db: DbSession,
    offset: Offset = 0,
    limit: Limit = 100,
) -> list[ResearchRead]:
    return ResearchRepository(db).list(offset=offset, limit=limit)


@router.post(
    "/researches",
    response_model=ResearchRead,
    status_code=status.HTTP_201_CREATED,
)
def create_research(payload: ResearchCreate, db: DbSession) -> ResearchRead:
    return ResearchRepository(db).create(payload)


@router.get("/researches/{research_id}", response_model=ResearchRead)
def get_research(research_id: int, db: DbSession) -> ResearchRead:
    try:
        return ResearchRepository(db).get(research_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.patch("/researches/{research_id}", response_model=ResearchRead)
def update_research(
    research_id: int,
    payload: ResearchUpdate,
    db: DbSession,
) -> ResearchRead:
    try:
        return ResearchRepository(db).update(research_id, payload)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.delete(
    "/researches/{research_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_research(research_id: int, db: DbSession) -> HTTPResponse:
    try:
        ResearchRepository(db).delete(research_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error
    return HTTPResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/research-tasks", response_model=list[ResearchTaskRead])
def list_research_tasks(
    db: DbSession,
    research_id: int | None = None,
    offset: Offset = 0,
    limit: Limit = 100,
) -> list[ResearchTaskRead]:
    repository = ResearchTaskRepository(db)
    try:
        if research_id is not None:
            return repository.list_for_research(
                research_id,
                offset=offset,
                limit=limit,
            )
        return repository.list(offset=offset, limit=limit)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.post(
    "/research-tasks",
    response_model=ResearchTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_research_task(
    payload: ResearchTaskCreate,
    db: DbSession,
) -> ResearchTaskRead:
    try:
        return ResearchTaskRepository(db).create(payload)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.get("/research-tasks/{task_id}", response_model=ResearchTaskRead)
def get_research_task(task_id: int, db: DbSession) -> ResearchTaskRead:
    try:
        return ResearchTaskRepository(db).get(task_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.patch("/research-tasks/{task_id}", response_model=ResearchTaskRead)
def update_research_task(
    task_id: int,
    payload: ResearchTaskUpdate,
    db: DbSession,
) -> ResearchTaskRead:
    try:
        return ResearchTaskRepository(db).update(task_id, payload)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.delete(
    "/research-tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_research_task(task_id: int, db: DbSession) -> HTTPResponse:
    try:
        ResearchTaskRepository(db).delete(task_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error
    return HTTPResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/responses", response_model=list[ResponseRead])
def list_responses(
    db: DbSession,
    research_task_id: int | None = None,
    offset: Offset = 0,
    limit: Limit = 100,
) -> list[ResponseRead]:
    repository = ResponseRepository(db)
    try:
        if research_task_id is not None:
            return repository.list_for_task(
                research_task_id,
                offset=offset,
                limit=limit,
            )
        return repository.list(offset=offset, limit=limit)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.post(
    "/responses",
    response_model=ResponseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_response(payload: ResponseCreate, db: DbSession) -> ResponseRead:
    try:
        return ResponseRepository(db).create(payload)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.get("/responses/{response_id}", response_model=ResponseRead)
def get_response(response_id: int, db: DbSession) -> ResponseRead:
    try:
        return ResponseRepository(db).get(response_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.get(
    "/responses/{response_id}/extraction",
    response_model=ExtractionResultRead,
)
def get_response_extraction(
    response_id: int,
    db: DbSession,
) -> ExtractionResultRead:
    try:
        return ExtractionService(db).get(response_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.post(
    "/responses/{response_id}/extraction",
    response_model=ExtractionResultRead,
)
def extract_response(
    response_id: int,
    db: DbSession,
) -> ExtractionResultRead:
    try:
        return ExtractionService(db).extract(response_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error
    except ExtractionProcessingError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error


@router.patch("/responses/{response_id}", response_model=ResponseRead)
def update_response(
    response_id: int,
    payload: ResponseUpdate,
    db: DbSession,
) -> ResponseRead:
    try:
        return ResponseRepository(db).update(response_id, payload)
    except EntityNotFoundError as error:
        raise _not_found(error) from error


@router.delete(
    "/responses/{response_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_response(response_id: int, db: DbSession) -> HTTPResponse:
    try:
        ResponseRepository(db).delete(response_id)
    except EntityNotFoundError as error:
        raise _not_found(error) from error
    return HTTPResponse(status_code=status.HTTP_204_NO_CONTENT)
