from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from backend.app.analytics_source import PlatformAnalyticsDataSource
from backend.app.database import get_db
from benchmark.repository import BenchmarkNotFoundError, SqlAlchemyBenchmarkRepository
from benchmark.schemas import BenchmarkRequest, BenchmarkResult, BenchmarkRunPage
from benchmark.service import BenchmarkDataUnavailableError, BenchmarkService

router = APIRouter(prefix="/benchmarks", tags=["benchmark"])
DbSession = Annotated[Session, Depends(get_db)]


def get_benchmark_service(db: DbSession) -> BenchmarkService:
    return BenchmarkService(PlatformAnalyticsDataSource(db), SqlAlchemyBenchmarkRepository(db))


Service = Annotated[BenchmarkService, Depends(get_benchmark_service)]


@router.post("", response_model=BenchmarkResult, status_code=status.HTTP_201_CREATED)
def create_benchmark(payload: BenchmarkRequest, service: Service) -> BenchmarkResult:
    try:
        return service.execute(payload)
    except BenchmarkDataUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@router.get("", response_model=BenchmarkRunPage)
def list_benchmarks(
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BenchmarkRunPage:
    return service.list(page, page_size)


@router.get("/{id}", response_model=BenchmarkResult)
def get_benchmark(
    benchmark_id: Annotated[int, Path(alias="id", ge=1)], service: Service
) -> BenchmarkResult:
    try:
        return service.get(benchmark_id)
    except BenchmarkNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
