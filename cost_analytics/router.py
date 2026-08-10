from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from cost_analytics.schemas import CostAnalyticsRead
from cost_analytics.service import CostAnalyticsService

router = APIRouter(prefix="/providers", tags=["cost-analytics"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/costs", response_model=CostAnalyticsRead)
def provider_costs(db: DbSession) -> CostAnalyticsRead:
    return CostAnalyticsService(db).report()
