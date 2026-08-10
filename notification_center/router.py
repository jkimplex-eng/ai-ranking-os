from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from notification_center.dependencies import build_notification_service
from notification_center.models import NotificationCategory, NotificationPriority
from notification_center.schemas import (
    NotificationEventCreate,
    NotificationRead,
    NotificationSummary,
)
from notification_center.service import NotificationNotFoundError

router = APIRouter(prefix="/notifications", tags=["notification-center"])
DbSession = Annotated[Session, Depends(get_db)]


def _user_id(request: Request) -> int:
    principal = getattr(request.state, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 1)))


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    request: Request,
    db: DbSession,
    unread_only: bool = False,
    category: NotificationCategory | None = None,
    priority: NotificationPriority | None = None,
    archived: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[NotificationRead]:
    return build_notification_service(db).list(
        _user_id(request),
        unread_only,
        category=category.value if category else None,
        priority=priority.value if priority else None,
        archived=archived,
        offset=offset,
        limit=limit,
    )


@router.get("/summary", response_model=NotificationSummary)
def notification_summary(request: Request, db: DbSession) -> NotificationSummary:
    return build_notification_service(db).summary(_user_id(request))


@router.post("/events", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def publish_notification(
    payload: NotificationEventCreate, request: Request, db: DbSession
) -> NotificationRead:
    try:
        return build_notification_service(db).emit(
            payload.event_type.value,
            payload.title,
            payload.message,
            user_id=_user_id(request),
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            metadata=payload.metadata,
            channels=tuple(payload.channels),
            category=payload.category.value,
            priority=payload.priority.value,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int, request: Request, db: DbSession
) -> NotificationRead:
    try:
        return build_notification_service(db).mark_read(
            _user_id(request), notification_id
        )
    except NotificationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{notification_id}/archive", response_model=NotificationRead)
def archive_notification(
    notification_id: int, request: Request, db: DbSession
) -> NotificationRead:
    try:
        return build_notification_service(db).archive(_user_id(request), notification_id)
    except NotificationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
