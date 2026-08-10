from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status

from closed_beta.dependencies import BetaAdminId
from feedback_center.dependencies import CurrentUserId, FeedbackServiceDependency
from feedback_center.models import FeedbackPriority, FeedbackStatus, FeedbackType
from feedback_center.schemas import (
    FeedbackAdminUpdate,
    FeedbackBulkUpdate,
    FeedbackCreate,
    FeedbackHistoryRead,
    FeedbackRead,
)
from feedback_center.service import FeedbackNotFoundError

router = APIRouter(tags=["feedback-center"])


def _correlation(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid4())


@router.post("/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_feedback(
    payload: FeedbackCreate,
    request: Request,
    user_id: CurrentUserId,
    service: FeedbackServiceDependency,
) -> FeedbackRead:
    return service.create(user_id, payload, _correlation(request))


@router.get("/feedback", response_model=list[FeedbackRead])
def list_own_feedback(
    user_id: CurrentUserId, service: FeedbackServiceDependency
) -> list[FeedbackRead]:
    return service.list_user(user_id)


@router.get("/feedback/{feedback_id}", response_model=FeedbackRead)
def get_own_feedback(
    feedback_id: int, user_id: CurrentUserId, service: FeedbackServiceDependency
) -> FeedbackRead:
    try:
        return service.get_user(user_id, feedback_id)
    except FeedbackNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/admin/feedback", response_model=list[FeedbackRead])
def admin_feedback(
    service: FeedbackServiceDependency,
    _admin_id: BetaAdminId,
    search: str | None = Query(default=None, max_length=250),
    feedback_type: FeedbackType | None = None,
    priority: FeedbackPriority | None = None,
    feedback_status: Annotated[FeedbackStatus | None, Query(alias="status")] = None,
    sort_by: str = Query(default="created_at", pattern="^(created_at|updated_at|priority|status)$"),
    descending: bool = True,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[FeedbackRead]:
    rows = service.admin_list(
        search=search,
        feedback_type=feedback_type.value if feedback_type else None,
        priority=priority.value if priority else None,
        status=feedback_status.value if feedback_status else None,
        sort_by=sort_by,
        descending=descending,
    )
    return rows[offset : offset + limit]


@router.patch("/admin/feedback/{feedback_id}", response_model=FeedbackRead)
def update_feedback(
    feedback_id: int,
    payload: FeedbackAdminUpdate,
    request: Request,
    service: FeedbackServiceDependency,
    admin_id: BetaAdminId,
) -> FeedbackRead:
    try:
        return service.update(feedback_id, payload, str(admin_id), _correlation(request))
    except FeedbackNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/admin/feedback/bulk", response_model=list[FeedbackRead])
def bulk_update_feedback(
    payload: FeedbackBulkUpdate,
    request: Request,
    service: FeedbackServiceDependency,
    admin_id: BetaAdminId,
) -> list[FeedbackRead]:
    try:
        return service.bulk(payload, str(admin_id), _correlation(request))
    except FeedbackNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/admin/feedback/{feedback_id}/history", response_model=list[FeedbackHistoryRead]
)
def feedback_history(
    feedback_id: int,
    service: FeedbackServiceDependency,
    _admin_id: BetaAdminId,
) -> list[FeedbackHistoryRead]:
    try:
        return service.history(feedback_id)
    except FeedbackNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
