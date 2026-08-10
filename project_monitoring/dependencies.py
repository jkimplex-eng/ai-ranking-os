from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from project_monitoring.repository import MonitorRepository
from project_monitoring.service import ProjectMonitoringService
from scheduler.monitoring_adapter import SchedulerMonitorAdapter
from workspace.repository import ProjectRepository, WorkspaceRepository


def current_user_id(request: Request) -> int:
    principal = getattr(request.state, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 1)))


def monitoring_service(
    db: Annotated[Session, Depends(get_db)],
) -> ProjectMonitoringService:
    return ProjectMonitoringService(
        MonitorRepository(db),
        SchedulerMonitorAdapter(db),
        WorkspaceRepository(db),
        ProjectRepository(db),
    )


CurrentUserId = Annotated[int, Depends(current_user_id)]
MonitoringServiceDependency = Annotated[
    ProjectMonitoringService, Depends(monitoring_service)
]
