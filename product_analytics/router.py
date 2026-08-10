from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from closed_beta.dependencies import BetaAdminId
from product_analytics.dependencies import CurrentUserId, ProductAnalyticsDependency
from product_analytics.schemas import (
    AnalyticsFilters,
    AnalyticsPeriod,
    DashboardRead,
    EventBatchCreate,
    EventRead,
    SessionRead,
    SessionStart,
)
from product_analytics.service import ProductAnalyticsError

router = APIRouter(prefix="/product-analytics", tags=["product-analytics"])


def _filters(
    organization_id: int | None,
    user_id: int | None,
    provider: str | None,
    template: str | None,
    region: str | None,
    language: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> AnalyticsFilters:
    return AnalyticsFilters(
        organization_id=organization_id,
        user_id=user_id,
        provider=provider,
        template=template,
        region=region,
        language=language,
        date_from=date_from,
        date_to=date_to,
    )


FilterText = Annotated[str | None, Query(max_length=100)]
PositiveId = Annotated[int | None, Query(ge=1)]


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(
    service: ProductAnalyticsDependency,
    _admin_id: BetaAdminId,
    period: AnalyticsPeriod = AnalyticsPeriod.DAILY,
    organization_id: PositiveId = None,
    user_id: PositiveId = None,
    provider: FilterText = None,
    template: FilterText = None,
    region: FilterText = None,
    language: FilterText = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DashboardRead:
    return service.dashboard(
        period,
        _filters(
            organization_id,
            user_id,
            provider,
            template,
            region,
            language,
            date_from,
            date_to,
        ),
    )


@router.post("/refresh", response_model=DashboardRead)
def refresh_dashboard(
    service: ProductAnalyticsDependency,
    _admin_id: BetaAdminId,
    period: AnalyticsPeriod = AnalyticsPeriod.DAILY,
) -> DashboardRead:
    return service.dashboard(period, AnalyticsFilters(), force=True)


@router.post("/events/batch", response_model=list[EventRead], status_code=201)
def ingest_events(
    payload: EventBatchCreate,
    service: ProductAnalyticsDependency,
    _admin_id: BetaAdminId,
) -> list[EventRead]:
    return service.record_batch(payload.events)


@router.get("/events", response_model=list[EventRead])
def list_events(
    service: ProductAnalyticsDependency,
    _admin_id: BetaAdminId,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[EventRead]:
    return service.list_events(offset, limit)


@router.post("/sessions", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def start_session(
    payload: SessionStart,
    user_id: CurrentUserId,
    service: ProductAnalyticsDependency,
) -> SessionRead:
    return service.start_session(user_id, payload)


@router.post("/sessions/{session_id}/finish", response_model=SessionRead)
def finish_session(
    session_id: str, user_id: CurrentUserId, service: ProductAnalyticsDependency
) -> SessionRead:
    try:
        return service.finish_session(session_id, user_id)
    except ProductAnalyticsError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/export/{format_name}")
def export_dashboard(
    format_name: str,
    service: ProductAnalyticsDependency,
    _admin_id: BetaAdminId,
    period: AnalyticsPeriod = AnalyticsPeriod.DAILY,
    organization_id: PositiveId = None,
    user_id: PositiveId = None,
    provider: FilterText = None,
    template: FilterText = None,
    region: FilterText = None,
    language: FilterText = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Response:
    try:
        content, media_type, filename = service.export(
            format_name.lower(),
            period,
            _filters(
                organization_id,
                user_id,
                provider,
                template,
                region,
                language,
                date_from,
                date_to,
            ),
        )
        return Response(
            content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ProductAnalyticsError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
