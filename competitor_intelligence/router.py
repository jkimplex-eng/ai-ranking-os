from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from competitor_intelligence.schemas import (
    CompetitorDashboardRead,
    DailyMonitoringRequest,
    SocialDashboardRead,
    SocialSourceCreate,
    SocialSourceRead,
)
from competitor_intelligence.service import CompetitorIntelligenceService
from competitor_intelligence.social_monitor import (
    CompetitorSocialMonitorService,
    SocialMonitorError,
)
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
                "Сначала выполните хотя бы одно исследование, которое станет ежедневным шаблоном."
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


@router.get(
    "/projects/{project_id}/competitors/{competitor_id}/social", response_model=SocialDashboardRead
)
def social_dashboard(
    project_id: int, competitor_id: int, user_id: CurrentUserId, db: DbSession
) -> SocialDashboardRead:
    try:
        return CompetitorSocialMonitorService(db).dashboard(user_id, project_id, competitor_id)
    except (ProjectNotFoundError, SocialMonitorError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/projects/{project_id}/competitors/{competitor_id}/social",
    response_model=SocialSourceRead,
    status_code=status.HTTP_201_CREATED,
)
def add_social_source(
    project_id: int,
    competitor_id: int,
    payload: SocialSourceCreate,
    user_id: CurrentUserId,
    db: DbSession,
) -> SocialSourceRead:
    try:
        return CompetitorSocialMonitorService(db).create(
            user_id, project_id, competitor_id, payload
        )
    except (ProjectNotFoundError, SocialMonitorError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/projects/{project_id}/competitors/{competitor_id}/social/refresh",
    response_model=SocialDashboardRead,
)
def refresh_social(
    project_id: int, competitor_id: int, user_id: CurrentUserId, db: DbSession
) -> SocialDashboardRead:
    try:
        return CompetitorSocialMonitorService(db).refresh(user_id, project_id, competitor_id)
    except (ProjectNotFoundError, SocialMonitorError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/projects/{project_id}/competitors/{competitor_id}/social/discover",
    response_model=SocialDashboardRead,
)
def discover_social(
    project_id: int, competitor_id: int, user_id: CurrentUserId, db: DbSession
) -> SocialDashboardRead:
    try:
        return CompetitorSocialMonitorService(db).discover(user_id, project_id, competitor_id)
    except (ProjectNotFoundError, SocialMonitorError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete(
    "/projects/{project_id}/competitors/{competitor_id}/social/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_social_source(
    project_id: int, competitor_id: int, source_id: int, user_id: CurrentUserId, db: DbSession
) -> Response:
    try:
        CompetitorSocialMonitorService(db).delete(user_id, project_id, competitor_id, source_id)
    except (ProjectNotFoundError, SocialMonitorError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
