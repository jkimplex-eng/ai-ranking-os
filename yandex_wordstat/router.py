from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from organization_workspace.repository import OrganizationRepository
from provider_connections.crypto import SecretCipher
from provider_connections.dependencies import default_organization
from yandex_wordstat.repository import WordstatRepository
from yandex_wordstat.schemas import (
    WordstatAnalyticsRead,
    WordstatConnectionCreate,
    WordstatConnectionRead,
    WordstatDiscoveryRequest,
    WordstatSnapshotRead,
)
from yandex_wordstat.service import WordstatError, WordstatService

router = APIRouter(prefix="/integrations/yandex-wordstat", tags=["yandex-wordstat"])
DbSession = Annotated[Session, Depends(get_db)]


def _identity(db: Session, request: Request, *, admin: bool = False) -> tuple[int, int]:
    principal = getattr(request.state, "principal", None)
    user_id = int(getattr(principal, "user_id", getattr(principal, "id", 1)))
    organization_id = default_organization(db, user_id)
    member = OrganizationRepository(db).member(organization_id, user_id)
    if member is None or (admin and member.role not in {"OWNER", "ADMIN"}):
        raise HTTPException(403, "Нет доступа к интеграции Wordstat")
    return organization_id, user_id


def _service(db: Session) -> WordstatService:
    settings = get_settings()
    return WordstatService(
        db,
        WordstatRepository(db),
        SecretCipher(settings.provider_secret_key or settings.auth_jwt_secret),
    )


def _error(error: WordstatError) -> HTTPException:
    return HTTPException(422, str(error))


@router.get("/status", response_model=WordstatConnectionRead)
def connection_status(request: Request, db: DbSession):
    organization_id, _ = _identity(db, request)
    return _service(db).status(organization_id)


@router.put("/connection", response_model=WordstatConnectionRead)
def connect(payload: WordstatConnectionCreate, request: Request, db: DbSession):
    organization_id, user_id = _identity(db, request, admin=True)
    try:
        return _service(db).connect(
            organization_id,
            user_id,
            payload.folder_id,
            payload.auth_type,
            payload.credential,
        )
    except WordstatError as error:
        raise _error(error) from error


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(request: Request, db: DbSession):
    organization_id, _ = _identity(db, request, admin=True)
    _service(db).disconnect(organization_id)
    return Response(status_code=204)


@router.post("/discover", response_model=WordstatSnapshotRead)
def discover(payload: WordstatDiscoveryRequest, request: Request, db: DbSession):
    organization_id, user_id = _identity(db, request)
    try:
        return _service(db).discover(organization_id, user_id, payload)
    except WordstatError as error:
        raise _error(error) from error


@router.get("/latest", response_model=WordstatSnapshotRead)
def latest(request: Request, db: DbSession, brand: str | None = Query(default=None)):
    organization_id, _ = _identity(db, request)
    try:
        return _service(db).latest(organization_id, brand)
    except WordstatError as error:
        raise HTTPException(404, str(error)) from error


@router.get("/analytics", response_model=WordstatAnalyticsRead)
def analytics(request: Request, db: DbSession, brand: str | None = Query(default=None)):
    organization_id, _ = _identity(db, request)
    try:
        return _service(db).analytics(organization_id, brand)
    except WordstatError as error:
        raise HTTPException(404, str(error)) from error
