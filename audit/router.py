from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from audit.repository import AuditRepository
from audit.schemas import AuditPage
from audit.service import AuditService
from backend.app.database import get_db

router = APIRouter(prefix="/audit", tags=["audit"])


def get_audit_service(db: Annotated[Session, Depends(get_db)]):
    return AuditService(AuditRepository(db))


Service = Annotated[AuditService, Depends(get_audit_service)]


@router.get("/events", response_model=AuditPage)
def search(
    service: Service,
    actor_id: str | None = None,
    action: str | None = None,
    category: str | None = None,
    correlation_id: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    return service.search(
        actor_id=actor_id,
        action=action,
        category=category,
        correlation_id=correlation_id,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
def export(service: Service, category: str | None = None):
    return StreamingResponse(
        service.export_csv(category=category, page=1, page_size=500),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit.csv"},
    )
