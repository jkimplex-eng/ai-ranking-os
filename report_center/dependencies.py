from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from report_center.repository import ReportCatalogRepository
from report_center.service import ReportCenterService
from research.report_center_adapter import SqlAlchemyReportSource


def report_center_service(
    db: Annotated[Session, Depends(get_db)],
) -> ReportCenterService:
    return ReportCenterService(ReportCatalogRepository(db), SqlAlchemyReportSource(db))


ReportCenterDependency = Annotated[
    ReportCenterService, Depends(report_center_service)
]
