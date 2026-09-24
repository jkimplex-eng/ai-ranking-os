from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from geo_site_audit.schemas import SiteAuditCreate, SiteAuditRead
from geo_site_audit.service import GeoSiteAuditService, SiteAuditError
from project_monitoring.dependencies import current_user_id
from workspace.repository import ProjectNotFoundError

router = APIRouter(prefix="/geo/site-audits", tags=["geo-site-audit"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUserId = Annotated[int, Depends(current_user_id)]


@router.post("", response_model=SiteAuditRead, status_code=status.HTTP_201_CREATED)
def run_audit(payload: SiteAuditCreate, user_id: CurrentUserId, db: DbSession) -> SiteAuditRead:
    try:
        return GeoSiteAuditService(db).run(user_id, payload)
    except (SiteAuditError, ProjectNotFoundError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("", response_model=list[SiteAuditRead])
def list_audits(
    user_id: CurrentUserId,
    db: DbSession,
    project_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SiteAuditRead]:
    return GeoSiteAuditService(db).list(user_id, project_id, limit)


@router.get("/{audit_id}", response_model=SiteAuditRead)
def get_audit(audit_id: int, user_id: CurrentUserId, db: DbSession) -> SiteAuditRead:
    try:
        return GeoSiteAuditService(db).get(user_id, audit_id)
    except SiteAuditError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
