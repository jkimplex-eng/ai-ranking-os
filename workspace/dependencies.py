from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from workspace.service import ProjectService, WorkspaceService


def current_user_id(request: Request) -> int:
    principal = getattr(request.state, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 1)))


def workspace_service(db: Annotated[Session, Depends(get_db)]) -> WorkspaceService:
    return WorkspaceService(db)


CurrentUserId = Annotated[int, Depends(current_user_id)]
WorkspaceServiceDependency = Annotated[WorkspaceService, Depends(workspace_service)]


def project_service(db: Annotated[Session, Depends(get_db)]) -> ProjectService:
    return ProjectService(db)


ProjectServiceDependency = Annotated[ProjectService, Depends(project_service)]
