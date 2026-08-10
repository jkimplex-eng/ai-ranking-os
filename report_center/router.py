from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from report_center.dependencies import ReportCenterDependency
from report_center.schemas import (
    ReportCatalogPage,
    ReportCatalogRead,
    ReportCatalogUpdate,
    ReportVersionComparison,
    ReportVersionRead,
)
from report_center.service import ReportNotFoundError

router = APIRouter(prefix="/reports", tags=["report-center"])


@router.get("", response_model=ReportCatalogPage)
def list_reports(
    service: ReportCenterDependency,
    project_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None, max_length=200),
    tag: str | None = Query(default=None, max_length=100),
    archived: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> ReportCatalogPage:
    return service.list(
        project_id=project_id,
        search=search,
        tag=tag,
        archived=archived,
        offset=offset,
        limit=limit,
    )


@router.patch("/{research_id}", response_model=ReportCatalogRead)
def update_report(
    research_id: int,
    payload: ReportCatalogUpdate,
    service: ReportCenterDependency,
) -> ReportCatalogRead:
    try:
        return service.update(research_id, payload)
    except ReportNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{research_id}/export", response_class=JSONResponse)
def export_report(research_id: int, service: ReportCenterDependency) -> JSONResponse:
    try:
        return JSONResponse(
            service.export(research_id),
            headers={
                "Content-Disposition": f'attachment; filename="report-{research_id}.json"'
            },
        )
    except ReportNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{research_id}/versions", response_model=ReportVersionRead)
def create_report_version(
    research_id: int, service: ReportCenterDependency
) -> ReportVersionRead:
    try:
        return service.snapshot(research_id)
    except ReportNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{research_id}/versions", response_model=list[ReportVersionRead])
def list_report_versions(
    research_id: int, service: ReportCenterDependency
) -> list[ReportVersionRead]:
    try:
        return service.versions(research_id)
    except ReportNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/{research_id}/versions/compare", response_model=ReportVersionComparison
)
def compare_report_versions(
    research_id: int,
    service: ReportCenterDependency,
    left: int = Query(ge=1),
    right: int = Query(ge=1),
) -> ReportVersionComparison:
    try:
        return service.compare_versions(research_id, left, right)
    except ReportNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
