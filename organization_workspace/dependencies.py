from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from organization_workspace.repository import OrganizationRepository
from organization_workspace.service import OrganizationService


def service(db: Annotated[Session, Depends(get_db)]):
    return OrganizationService(OrganizationRepository(db))


def user_id(request: Request):
    principal = getattr(request.state, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 1)))


OrganizationServiceDependency = Annotated[OrganizationService, Depends(service)]
CurrentUserId = Annotated[int, Depends(user_id)]
