from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from organization_workspace.repository import OrganizationRepository
from provider_connections.crypto import SecretCipher
from provider_connections.dependencies import default_organization
from yandex_intelligence.schemas import YandexIntelligenceRead, YandexQuerySeedsRead
from yandex_intelligence.service import YandexIntelligenceError, YandexIntelligenceService
from yandex_webmaster.repository import YandexWebmasterRepository
from yandex_webmaster.service import YandexWebmasterError, YandexWebmasterService

router = APIRouter(prefix="/yandex-intelligence", tags=["yandex-intelligence"])
DbSession = Annotated[Session, Depends(get_db)]


def _identity(db: Session, request: Request) -> tuple[int, int]:
    principal = getattr(request.state, "principal", None)
    user_id = int(getattr(principal, "user_id", getattr(principal, "id", 1)))
    organization_id = default_organization(db, user_id)
    if OrganizationRepository(db).member(organization_id, user_id) is None:
        raise HTTPException(403, "Нет доступа к организации")
    return organization_id, user_id


def _service(db: Session) -> YandexIntelligenceService:
    settings = get_settings()
    webmaster = YandexWebmasterService(
        YandexWebmasterRepository(db),
        SecretCipher(settings.provider_secret_key or settings.auth_jwt_secret),
        settings,
    )
    return YandexIntelligenceService(db, webmaster)


@router.post("/sync", response_model=YandexIntelligenceRead)
def sync(request: Request, db: DbSession):
    organization_id, _ = _identity(db, request)
    try:
        return _service(db).sync(organization_id)
    except (YandexIntelligenceError, YandexWebmasterError) as error:
        raise HTTPException(422, str(error)) from error


@router.get("/dashboard", response_model=YandexIntelligenceRead)
def dashboard(request: Request, db: DbSession):
    organization_id, _ = _identity(db, request)
    try:
        return _service(db).latest(organization_id)
    except YandexIntelligenceError as error:
        raise HTTPException(404, str(error)) from error


@router.get("/query-seeds", response_model=YandexQuerySeedsRead)
def query_seeds(request: Request, db: DbSession, website_url: str | None = Query(default=None)):
    organization_id, _ = _identity(db, request)
    try:
        return _service(db).query_seeds(organization_id, website_url)
    except YandexIntelligenceError as error:
        raise HTTPException(404, str(error)) from error
