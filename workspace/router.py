from fastapi import APIRouter

from workspace.dependencies import CurrentUserId, WorkspaceServiceDependency
from workspace.schemas import WorkspaceRead, WorkspaceUpdate

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
