from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from competitor_intelligence.schemas import CompetitorDashboardRead, DailyMonitoringRequest
from competitor_intelligence.service import CompetitorIntelligenceService
from project_monitoring.dependencies import current_user_id
from project_monitoring.repository import MonitorRepository
from project_monitoring.schemas import MonitorFrequency, MonitorModel, ProjectMonitorUpsert
from project_monitoring.service import MonitorNotFoundError, ProjectMonitoringService
from research.models import Research, ResearchStatus, ResearchTask
from scheduler.monitoring_adapter import SchedulerMonitorAdapter
from workspace.repository import ProjectNotFoundError, ProjectRepository, WorkspaceRepository

router = APIRouter(prefix="/competitor-intelligence", tags=["competitor-intelligence"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUserId = Annotated[int, Depends(current_user_id)]


@router.get("/projects/{project_id}", response_model=CompetitorDashboardRead)
def dashboard(project_id: int, user_id: CurrentUserId, db: DbSession) -> CompetitorDashboardRead:
    try:
        return CompetitorIntelligenceService(db).dashboard(user_id, project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/projects/{project_id}/refresh", response_model=CompetitorDashboardRead)
def refresh(project_id: int, user_id: CurrentUserId, db: DbSession) -> CompetitorDashboardRead:
    try:
        return CompetitorIntelligenceService(db).refresh_project(user_id, project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put("/projects/{project_id}/daily-monitoring", response_model=CompetitorDashboardRead)
def daily_monitoring(
    project_id: int,
    payload: DailyMonitoringRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> CompetitorDashboardRead:
    monitoring = ProjectMonitoringService(
        MonitorRepository(db),
        SchedulerMonitorAdapter(db),
        WorkspaceRepository(db),
        ProjectRepository(db),
    )
    if not payload.enabled:
        with suppress(MonitorNotFoundError):
            monitoring.delete(user_id, project_id)
        return CompetitorIntelligenceService(db).dashboard(user_id, project_id)
    template = (
        db.get(Research, payload.template_research_id)
        if payload.template_research_id
        else db.scalar(
            select(Research)
            .where(Research.project_id == project_id, Research.status == ResearchStatus.COMPLETED)
            .order_by(Research.created_at.desc())
        )
    )
    if template is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Сначала выполните хотя бы одно исследование, "
                "которое станет ежедневным шаблоном."
            ),
        )
    rows = db.execute(
        select(ResearchTask.provider, ResearchTask.model)
        .where(ResearchTask.research_id == template.id, ResearchTask.provider.is_not(None))
        .distinct()
    )
    models = [
        MonitorModel(provider=provider, model=model)
        for provider, model in rows
        if provider and model
    ]
    if not models:
        raise HTTPException(status_code=422, detail="В исследовании-шаблоне нет выбранных моделей.")
    try:
        monitoring.upsert(
            user_id,
            project_id,
            ProjectMonitorUpsert(
                template_research_id=template.id,
                frequency=MonitorFrequency.DAILY,
                models=models,
                query=template.objective,
                enabled=True,
            ),
        )
    except (ProjectNotFoundError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return CompetitorIntelligenceService(db).dashboard(user_id, project_id)
