from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import get_settings
from provider_connections.dependencies import default_organization
from geo_platforms.repository import PlatformRepository
from geo_platforms.schemas import (
    DiscoveryRequest,
    DiscoveryResult,
    ImportRead,
    ImportRequest,
    PlatformCreate,
    PlatformRead,
    PlatformUpdate,
    ObservedSourceCreate,
)
from geo_platforms.service import PlatformNotFoundError, PlatformService

def require_platform_scope(request: Request, db: Annotated[Session, Depends(get_db)]) -> None:
    if not get_settings().security_enforce_auth:
        return
    principal = getattr(request.state, "principal", None)
    user_id = getattr(principal, "user_id", getattr(principal, "owner_id", getattr(principal, "id", None)))
    if user_id is None:
        raise HTTPException(401, "Authentication required")
    db.info["geo_organization_id"] = default_organization(db, int(user_id))
    db.info["geo_user_id"] = int(user_id)


router = APIRouter(
    prefix="/geo/platforms", tags=["geo-platforms"],
    dependencies=[Depends(require_platform_scope)],
)
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=PlatformRead, status_code=status.HTTP_201_CREATED)
def create_platform(payload: PlatformCreate, db: DbSession) -> PlatformRead:
    try:
        return PlatformService(PlatformRepository(db)).create(payload)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/observed/{research_id}", response_model=PlatformRead)
def register_observed_source(
    research_id: int, payload: ObservedSourceCreate, db: DbSession
) -> PlatformRead:
    try:
        return PlatformService(PlatformRepository(db)).register_observed(
            research_id, payload.domain
        )
    except PlatformNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("", response_model=list[PlatformRead])
def list_platforms(
    db: DbSession,
    category: str | None = None,
    language: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PlatformRead]:
    return PlatformRepository(db).list(category=category, language=language)[
        offset : offset + limit
    ]


@router.get("/{platform_id}", response_model=PlatformRead)
def get_platform(platform_id: UUID, db: DbSession) -> PlatformRead:
    item = PlatformRepository(db).get(platform_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")
    return item


@router.patch("/{platform_id}", response_model=PlatformRead)
def update_platform(platform_id: UUID, payload: PlatformUpdate, db: DbSession) -> PlatformRead:
    try:
        return PlatformService(PlatformRepository(db)).update(platform_id, payload)
    except PlatformNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform(platform_id: UUID, db: DbSession) -> None:
    try:
        PlatformService(PlatformRepository(db)).delete(platform_id)
    except PlatformNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/imports", response_model=ImportRead, status_code=status.HTTP_201_CREATED)
def import_platforms(payload: ImportRequest, db: DbSession) -> ImportRead:
    try:
        return PlatformService(PlatformRepository(db)).import_rows(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/discover", response_model=DiscoveryResult)
def discover_platforms(payload: DiscoveryRequest, db: DbSession) -> DiscoveryResult:
    try:
        created, existing, platforms = PlatformService(PlatformRepository(db)).discover(payload)
        return DiscoveryResult(created=created, existing=existing, platforms=platforms)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
