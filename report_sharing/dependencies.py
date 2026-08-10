from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from audit.repository import AuditRepository
from audit.service import AuditService
from backend.app.database import get_db
from report_sharing.repository import ShareRepository
from report_sharing.service import ShareService
from research.report_center_adapter import SqlAlchemyReportSource


def share_service(db: Annotated[Session, Depends(get_db)]) -> ShareService:
    return ShareService(
        ShareRepository(db), SqlAlchemyReportSource(db), AuditService(AuditRepository(db))
    )


ShareServiceDependency = Annotated[ShareService, Depends(share_service)]
