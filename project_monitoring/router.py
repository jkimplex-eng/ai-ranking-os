from fastapi import APIRouter, HTTPException, Response, status

from project_monitoring.dependencies import CurrentUserId, MonitoringServiceDependency
from project_monitoring.schemas import ProjectMonitorRead, ProjectMonitorUpsert
from project_monitoring.service import MonitorNotFoundError
from workspace.repository import ProjectNotFoundError

router = APIRouter(prefix="/workspace/projects", tags=["project-monitoring"])


@router.get("/{project_id}/monitoring", response_model=ProjectMonitorRead)
def get_monitoring(
    project_id: int,
    user_id: CurrentUserId,
    service: MonitoringServiceDependency,
) -> ProjectMonitorRead:
    try:
        return service.get(user_id, project_id)
    except (MonitorNotFoundError, ProjectNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put("/{project_id}/monitoring", response_model=ProjectMonitorRead)
def configure_monitoring(
    project_id: int,
    payload: ProjectMonitorUpsert,
    user_id: CurrentUserId,
    service: MonitoringServiceDependency,
) -> ProjectMonitorRead:
    try:
        return service.upsert(user_id, project_id, payload)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{project_id}/monitoring", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitoring(
    project_id: int,
    user_id: CurrentUserId,
    service: MonitoringServiceDependency,
) -> Response:
    try:
        service.delete(user_id, project_id)
    except (MonitorNotFoundError, ProjectNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
