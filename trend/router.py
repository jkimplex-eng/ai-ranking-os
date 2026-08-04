from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from trend.ports import TrendDataUnavailableError
from trend.research_adapter import build_trend_engine
from trend.schemas import MetricTrend, TrendMetric, TrendSeriesRead

router = APIRouter(prefix="/entities", tags=["trend"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{entity_id}/trend", response_model=TrendSeriesRead)
def get_entity_trend(entity_id: UUID, db: DbSession) -> TrendSeriesRead:
    try:
        return build_trend_engine(db).build(entity_id)
    except TrendDataUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{entity_id}/trend/{metric}", response_model=MetricTrend)
def get_entity_metric_trend(
    entity_id: UUID, metric: TrendMetric, db: DbSession
) -> MetricTrend:
    try:
        series = build_trend_engine(db).build(entity_id)
    except TrendDataUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return next(item for item in series.metrics if item.metric == metric)

