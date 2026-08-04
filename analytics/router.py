from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from analytics.repository import AnalyticsRunNotFoundError, SqlAlchemyAnalyticsRepository
from analytics.schemas import AnalyticsQuery, AnalyticsResult, AnalyticsRunPage
from analytics.service import AnalyticsMetricNotFoundError, AnalyticsService
from backend.app.analytics_source import PlatformAnalyticsDataSource
from backend.app.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])
DbSession = Annotated[Session, Depends(get_db)]


def get_analytics_service(db: DbSession) -> AnalyticsService:
    return AnalyticsService(PlatformAnalyticsDataSource(db), SqlAlchemyAnalyticsRepository(db))


AnalyticsServiceDependency = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.post("/query", response_model=AnalyticsResult, status_code=status.HTTP_201_CREATED)
def execute_analytics_query(
    payload: AnalyticsQuery, service: AnalyticsServiceDependency
) -> AnalyticsResult:
    try:
        return service.execute(payload)
    except AnalyticsMetricNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@router.get("/runs", response_model=AnalyticsRunPage)
def list_analytics_runs(
    service: AnalyticsServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AnalyticsRunPage:
    return service.list(page, page_size)


@router.get("/runs/{id}", response_model=AnalyticsResult)
def get_analytics_run(
    run_id: Annotated[int, Path(alias="id", ge=1)], service: AnalyticsServiceDependency
) -> AnalyticsResult:
    try:
        return service.get(run_id)
    except AnalyticsRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
