from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from product_analytics.repository import ProductAnalyticsRepository
from product_analytics.service import ProductAnalyticsService


def analytics_service(
    db: Annotated[Session, Depends(get_db)],
) -> ProductAnalyticsService:
    return ProductAnalyticsService(ProductAnalyticsRepository(db))


def current_user_id(request: Request) -> int:
    principal = getattr(request.state, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 1)))


ProductAnalyticsDependency = Annotated[
    ProductAnalyticsService, Depends(analytics_service)
]
CurrentUserId = Annotated[int, Depends(current_user_id)]
