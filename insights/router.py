from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from backend.app.analytics_source import PlatformAnalyticsDataSource
from backend.app.database import get_db
from insights.repository import InsightRunNotFoundError, SqlAlchemyInsightRepository
from insights.schemas import InsightRequest, InsightResult, InsightRunPage
from insights.service import InsightDataUnavailableError, InsightService

router = APIRouter(prefix="/insights", tags=["insights"])
DbSession = Annotated[Session, Depends(get_db)]


def get_insight_service(db: DbSession) -> InsightService:
    return InsightService(PlatformAnalyticsDataSource(db), SqlAlchemyInsightRepository(db))


Service = Annotated[InsightService, Depends(get_insight_service)]


@router.post("/generate", response_model=InsightResult, status_code=status.HTTP_201_CREATED)
def generate_insights(payload: InsightRequest, service: Service) -> InsightResult:
    try:
        return service.generate(payload)
    except InsightDataUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@router.get("/runs", response_model=InsightRunPage)
def list_insight_runs(
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> InsightRunPage:
    return service.list(page, page_size)


@router.get("/runs/{id}", response_model=InsightResult)
def get_insight_run(
    run_id: Annotated[int, Path(alias="id", ge=1)], service: Service
) -> InsightResult:
    try:
        return service.get(run_id)
    except InsightRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
