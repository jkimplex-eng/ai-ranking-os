from fastapi import APIRouter, HTTPException, Query, Response, status

from workspace.dependencies import (
    CurrentUserId,
    ProjectServiceDependency,
    WorkspaceServiceDependency,
)
from workspace.repository import ProjectNotFoundError
from workspace.schemas import (
    CompetitorCreate,
    CompetitorImport,
    CompetitorRead,
    CompetitorUpdate,
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


@router.get("/projects/{project_id}/competitors", response_model=list[CompetitorRead])
def list_competitors(
    project_id: int, user_id: CurrentUserId, service: ProjectServiceDependency
) -> list[CompetitorRead]:
    try:
        return service.list_competitors(user_id, project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/projects/{project_id}/competitors",
    response_model=CompetitorRead,
    status_code=status.HTTP_201_CREATED,
)
def create_competitor(
    project_id: int,
    payload: CompetitorCreate,
    user_id: CurrentUserId,
    service: ProjectServiceDependency,
) -> CompetitorRead:
    try:
        return service.create_competitor(user_id, project_id, payload)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/projects/{project_id}/competitors/{competitor_id}", response_model=CompetitorRead)
def update_competitor(
    project_id: int,
    competitor_id: int,
    payload: CompetitorUpdate,
    user_id: CurrentUserId,
    service: ProjectServiceDependency,
) -> CompetitorRead:
    try:
        return service.update_competitor(user_id, project_id, competitor_id, payload)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete(
    "/projects/{project_id}/competitors/{competitor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_competitor(
    project_id: int,
    competitor_id: int,
    user_id: CurrentUserId,
    service: ProjectServiceDependency,
) -> Response:
    try:
        service.delete_competitor(user_id, project_id, competitor_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/projects/{project_id}/competitors/import", response_model=list[CompetitorRead])
def import_competitors(
    project_id: int,
    payload: CompetitorImport,
    user_id: CurrentUserId,
    service: ProjectServiceDependency,
) -> list[CompetitorRead]:
    try:
        return service.import_competitors(user_id, project_id, payload)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
