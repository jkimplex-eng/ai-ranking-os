from contextlib import suppress
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.llm_router.ports import LLMRouterPort
from backend.app.llm_router.schemas import RouteRequest
from backend.app.llm_router.service import router_service
from decision_center import service as decision_service
from decision_center.models import AgentType, Task, TaskPriority, TaskStatus
from decision_center.schemas import TaskCreate, TaskUpdate
from execution_engine import service as execution_service
from execution_engine.models import ExecutionState
from execution_engine.worker_manager import WorkerManager
from research.extraction import ExtractionProcessingError, ExtractionService
from research.models import Research, ResearchStatus, ResearchTask, ResearchTaskStatus, Response
from research.normalizer import (
    NormalizedResponse,
    ResponseErrorType,
    ResponseNormalizationError,
    classify_error,
    normalize,
    normalize_error,
)
from research.repositories import ResearchRepository, ResearchTaskRepository
from research.schemas import ResearchRunRequest, ResearchTaskCreate


class ResearchRunConflictError(ValueError):
    """Research cannot start from its current state."""


def _update_progress(
    db: Session,
    research: Research,
    *,
    completed: int,
    failed: int,
) -> None:
    research.completed_tasks = completed
    research.failed_tasks = failed
    processed = completed + failed
    research.progress_percent = round(
        processed / research.total_tasks * 100,
        2,
    ) if research.total_tasks else 100.0
    db.commit()


def _provider_worker(
    tasks_by_decision_id: dict[int, ResearchTask],
    router_context: tuple[Session, LLMRouterPort],
) -> WorkerManager:
    db, llm_router = router_context
    def execute(task: Task) -> dict:
        research_task = tasks_by_decision_id[task.id]
        return llm_router.generate(
            db,
            RouteRequest(
                query=research_task.query,
                profile=research_task.metadata_payload.get("routing_profile", "BALANCED"),
                allowed_models=research_task.metadata_payload.get("allowed_models", []),
                task_type="research",
                metadata={
                    "research_id": research_task.research_id,
                    "research_task_id": research_task.id,
                    "target_entity": research_task.research.metadata_payload.get(
                        "target_entity", research_task.research.title
                    ),
                },
            ),
        )

    return WorkerManager(
        {
            AgentType.CODEX: execute,
            AgentType.QWEN: execute,
            AgentType.DEEPSEEK: execute,
        }
    )


def _save_response(
    db: Session,
    research_task: ResearchTask,
    *,
    normalized: NormalizedResponse,
    raw_response: dict,
    latency_ms: int | None,
    finished_at: datetime,
    error_type: ResponseErrorType | None = None,
    error_message: str | None = None,
) -> Response:
    usage = normalized.usage
    response = Response(
        research_task_id=research_task.id,
        provider=str(research_task.provider),
        model=str(research_task.model),
        prompt=research_task.query,
        raw_response=raw_response,
        normalized_response=normalized.model_dump(mode="json"),
        latency_ms=latency_ms,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        cost=usage.cost,
        finished_at=finished_at,
        error_type=error_type,
        error_message=error_message,
        # Backward-compatible TASK-302 fields.
        content=normalized.content,
        raw_payload=raw_response,
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
    )
    db.add(response)
    db.commit()
    db.refresh(response)
    with suppress(ExtractionProcessingError):
        ExtractionService(db).extract(response.id)
    db.refresh(response)
    return response


def _save_error_response(
    db: Session,
    research_task: ResearchTask,
    message: str,
    *,
    latency_ms: int | None = None,
    finished_at: datetime | None = None,
) -> Response:
    error_type = classify_error(message)
    return _save_response(
        db,
        research_task,
        normalized=normalize_error(error_type, message),
        raw_response={"error": message, "error_type": error_type},
        latency_ms=latency_ms,
        finished_at=finished_at or datetime.now(UTC),
        error_type=error_type,
        error_message=message,
    )


def run_research(
    db: Session,
    research_id: int,
    payload: ResearchRunRequest,
    *,
    manager: WorkerManager | None = None,
    llm_router: LLMRouterPort = router_service,
    allow_active: bool = False,
) -> Research:
    research = ResearchRepository(db).get(research_id)
    if research.status in {
        *(() if allow_active else (ResearchStatus.ACTIVE,)),
        ResearchStatus.COMPLETED,
        ResearchStatus.ARCHIVED,
    }:
        raise ResearchRunConflictError(
            f"Research {research_id} in {research.status} cannot be run"
        )

    research.status = ResearchStatus.ACTIVE
    selections = payload.models or [None]
    research.total_tasks = len(selections)
    research.completed_tasks = 0
    research.failed_tasks = 0
    research.progress_percent = 0
    db.commit()

    query = payload.query or research.objective or research.title
    research_tasks = []
    task_repository = ResearchTaskRepository(db)
    for selection in selections:
        selected_provider = selection.provider if selection else None
        selected_model = selection.model if selection else None
        research_task = task_repository.create(
            ResearchTaskCreate(
                research_id=research.id,
                query=query,
                provider=selected_provider,
                model=selected_model,
                metadata={
                    "source": "research-run",
                    "routing_profile": payload.routing_profile,
                    "allowed_models": [selected_model] if selected_model else [],
                },
            )
        )
        decision_task = decision_service.create_task(
            db,
            TaskCreate(
                title=f"Research {research.id}: {selected_model or payload.routing_profile}",
                description=query,
                status=TaskStatus.READY,
                priority=TaskPriority.MEDIUM,
            ),
        )
        research_task.decision_task_id = decision_task.id
        db.commit()
        research_tasks.append(research_task)

    tasks_by_decision_id = {
        int(item.decision_task_id): item
        for item in research_tasks
        if item.decision_task_id is not None
    }
    worker_manager = manager or _provider_worker(
        tasks_by_decision_id,
        (db, llm_router),
    )
    completed = 0
    failed = 0
    for research_task in research_tasks:
        research_task.status = ResearchTaskStatus.RUNNING
        db.commit()
        try:
            execution = execution_service.start_task_execution(
                db,
                research_task.decision_task_id,
                worker_manager,
                retry_base_seconds=get_settings().execution_retry_base_seconds,
            )
            research_task.execution_id = execution.id
            if execution.state == ExecutionState.COMPLETED:
                try:
                    raw_response = execution.result or {}
                    research_task.provider = str(
                        raw_response.get("provider", research_task.provider or "router")
                    )
                    research_task.model = str(
                        raw_response.get("model", research_task.model or "router-selected")
                    )
                    normalized = normalize(raw_response)
                    _save_response(
                        db,
                        research_task,
                        normalized=normalized,
                        raw_response=raw_response,
                        latency_ms=execution.duration_ms,
                        finished_at=execution.finished_at or datetime.now(UTC),
                    )
                    research_task.status = ResearchTaskStatus.COMPLETED
                    completed += 1
                except ResponseNormalizationError as error:
                    research_task.status = ResearchTaskStatus.FAILED
                    research_task.error = str(error)
                    _save_response(
                        db,
                        research_task,
                        normalized=normalize_error(error.error_type, str(error)),
                        raw_response=execution.result or {},
                        latency_ms=execution.duration_ms,
                        finished_at=execution.finished_at or datetime.now(UTC),
                        error_type=error.error_type,
                        error_message=str(error),
                    )
                    failed += 1
            else:
                research_task.status = ResearchTaskStatus.FAILED
                research_task.error = execution.error or f"Execution in {execution.state}"
                _save_error_response(
                    db,
                    research_task,
                    research_task.error,
                    latency_ms=execution.duration_ms,
                    finished_at=execution.finished_at,
                )
                failed += 1
        except execution_service.ExecutionEngineError as error:
            research_task.status = ResearchTaskStatus.FAILED
            research_task.error = str(error)
            decision_service.update_task(
                db,
                research_task.decision_task_id,
                TaskUpdate(status=TaskStatus.BLOCKED),
            )
            _save_error_response(db, research_task, str(error))
            failed += 1
        db.commit()
        _update_progress(
            db,
            research,
            completed=completed,
            failed=failed,
        )

    research.status = (
        ResearchStatus.COMPLETED if failed == 0 else ResearchStatus.FAILED
    )
    research.progress_percent = 100.0
    db.commit()
    db.refresh(research)
    return research
