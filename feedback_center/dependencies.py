from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from audit.repository import AuditRepository
from audit.service import AuditService
from backend.app.database import get_db
from feedback_center.repository import FeedbackRepository
from feedback_center.service import FeedbackService


def feedback_service(db: Annotated[Session, Depends(get_db)]) -> FeedbackService:
    return FeedbackService(FeedbackRepository(db), AuditService(AuditRepository(db)))


def current_user_id(request: Request) -> int:
    principal = getattr(request.state, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 1)))


FeedbackServiceDependency = Annotated[FeedbackService, Depends(feedback_service)]
CurrentUserId = Annotated[int, Depends(current_user_id)]
