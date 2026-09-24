from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from organization_workspace.repository import OrganizationRepository
from provider_connections.crypto import SecretCipher
from provider_connections.dependencies import default_organization
from yandex_webmaster.repository import YandexWebmasterRepository
from yandex_webmaster.schemas import (
    AuthorizationRead,
    ConnectionRead,
    HostRead,
    HostSelection,
    QueryRead,
    WebmasterEvidenceRead,
)
from yandex_webmaster.service import YandexWebmasterError, YandexWebmasterService

router = APIRouter(prefix="/integrations/yandex-webmaster", tags=["yandex-webmaster"])
DbSession = Annotated[Session, Depends(get_db)]


def _service(db: Session) -> YandexWebmasterService:
    settings = get_settings()
    return YandexWebmasterService(
        YandexWebmasterRepository(db),
        SecretCipher(settings.provider_secret_key or settings.auth_jwt_secret),
        settings,
    )


def _identity(db: Session, request: Request) -> tuple[int, int]:
    principal = getattr(request.state, "principal", None)
    user_id = int(getattr(principal, "user_id", getattr(principal, "id", 1)))
    organization_id = default_organization(db, user_id)
    member = OrganizationRepository(db).member(organization_id, user_id)
    if member is None or member.role not in {"OWNER", "ADMIN"}:
        raise HTTPException(403, "Требуются права администратора организации")
    return organization_id, user_id


def _error(error: YandexWebmasterError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


@router.get("/status", response_model=ConnectionRead)
def connection_status(request: Request, db: DbSession):
    organization_id, _ = _identity(db, request)
    return _service(db).read(YandexWebmasterRepository(db).connection(organization_id))


@router.post("/authorize", response_model=AuthorizationRead)
def authorize(request: Request, db: DbSession):
    organization_id, user_id = _identity(db, request)
    try:
        return AuthorizationRead(
            authorization_url=_service(db).authorization_url(organization_id, user_id)
        )
    except YandexWebmasterError as error:
        raise _error(error) from error


@router.get("/callback", include_in_schema=False)
def callback(db: DbSession, code: str = Query(min_length=1), state: str = Query(min_length=1)):
    try:
        _service(db).complete(code, state)
    except YandexWebmasterError:
        return RedirectResponse("/settings?yandex_webmaster=error", status_code=303)
    return RedirectResponse("/settings?yandex_webmaster=connected", status_code=303)


@router.get("/hosts", response_model=list[HostRead])
def hosts(request: Request, db: DbSession):
    organization_id, _ = _identity(db, request)
    try:
        return _service(db).hosts(organization_id)
    except YandexWebmasterError as error:
        raise _error(error) from error


@router.put("/host", response_model=ConnectionRead)
def select_host(payload: HostSelection, request: Request, db: DbSession):
    organization_id, _ = _identity(db, request)
    try:
        return _service(db).select_host(organization_id, payload.host_id, payload.host_url)
    except YandexWebmasterError as error:
        raise _error(error) from error


@router.get("/queries", response_model=list[QueryRead])
def queries(request: Request, db: DbSession, limit: int = Query(default=100, ge=1, le=500)):
    organization_id, _ = _identity(db, request)
    try:
        return _service(db).popular_queries(organization_id, limit)
    except YandexWebmasterError as error:
        raise _error(error) from error


@router.get("/evidence", response_model=WebmasterEvidenceRead)
def evidence(request: Request, db: DbSession):
    organization_id, _ = _identity(db, request)
    try:
        return _service(db).evidence(organization_id)
    except YandexWebmasterError as error:
        raise _error(error) from error


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(request: Request, db: DbSession):
    organization_id, _ = _identity(db, request)
    _service(db).disconnect(organization_id)
    return Response(status_code=204)
