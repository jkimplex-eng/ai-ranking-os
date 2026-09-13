from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from organization_workspace.repository import OrganizationRepository
from provider_connections.dependencies import ConnectionService, default_organization
from provider_connections.schemas import ConnectionCreate, ConnectionRead, ConnectionTestRead
from provider_connections.service import ProviderConnectionError

router = APIRouter(prefix="/provider-connections", tags=["provider-connections"])
DbSession = Annotated[Session, Depends(get_db)]


def _user_id(request: Request) -> int:
    principal = getattr(request.state, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 1)))


def _organization(db: Session, request: Request, requested: int | None = None) -> tuple[int, int]:
    user_id = _user_id(request)
    try:
        organization_id = requested or default_organization(db, user_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    memberships = OrganizationRepository(db).member(organization_id, user_id)
    if memberships is None or memberships.role not in {"OWNER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Требуются права администратора организации")
    return organization_id, user_id


@router.get("", response_model=list[ConnectionRead])
def connections(request: Request, db: DbSession, service: ConnectionService):
    organization_id, _ = _organization(db, request)
    return service.list(organization_id)


@router.post("", response_model=ConnectionRead, status_code=status.HTTP_201_CREATED)
def connect(payload: ConnectionCreate, request: Request, db: DbSession, service: ConnectionService):
    organization_id, user_id = _organization(db, request, payload.organization_id)
    try:
        return service.create(organization_id, user_id, payload)
    except ProviderConnectionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{connection_id}/test", response_model=ConnectionTestRead)
def test_connection(
    connection_id: int, request: Request, db: DbSession, service: ConnectionService
):
    organization_id, _ = _organization(db, request)
    try:
        return service.test(connection_id, organization_id)
    except ProviderConnectionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(connection_id: int, request: Request, db: DbSession, service: ConnectionService):
    organization_id, user_id = _organization(db, request)
    try:
        service.delete(connection_id, organization_id, user_id)
    except ProviderConnectionError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=204)
