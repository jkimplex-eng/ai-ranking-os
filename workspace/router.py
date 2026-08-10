from fastapi import APIRouter, HTTPException, Query, Response, status

from workspace.dependencies import (
    CurrentUserId,
    ProjectServiceDependency,
    WorkspaceServiceDependency,
)
from workspace.repository import ProjectNotFoundError
from workspace.schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    WorkspaceRead,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("", response_model=WorkspaceRead)
def get_workspace(user_id: CurrentUserId, service: WorkspaceServiceDependency) -> WorkspaceRead:
    return service.get(user_id)


@router.patch("", response_model=WorkspaceRead)
def update_workspace(
    payload: WorkspaceUpdate,
    user_id: CurrentUserId,
    service: WorkspaceServiceDependency,
) -> WorkspaceRead:
    return service.update(user_id, payload)


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(
    user_id: CurrentUserId,
    service: ProjectServiceDependency,
    include_archived: bool = Query(default=False),
) -> list[ProjectRead]:
    return service.list(user_id, include_archived)


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate, user_id: CurrentUserId, service: ProjectServiceDependency
) -> ProjectRead:
    return service.create(user_id, payload)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int, user_id: CurrentUserId, service: ProjectServiceDependency
) -> ProjectRead:
    try:
        return service.get(user_id, project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    user_id: CurrentUserId,
    service: ProjectServiceDependency,
) -> ProjectRead:
    try:
        return service.update(user_id, project_id, payload)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int, user_id: CurrentUserId, service: ProjectServiceDependency
) -> Response:
    try:
        service.delete(user_id, project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
