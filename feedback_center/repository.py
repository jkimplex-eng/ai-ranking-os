from __future__ import annotations

from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session

from feedback_center.models import Feedback, FeedbackAttachment, FeedbackHistory


class FeedbackRepository:
    SORT_FIELDS = {
        "created_at": Feedback.created_at,
        "updated_at": Feedback.updated_at,
        "priority": Feedback.priority,
        "status": Feedback.status,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, item: Feedback) -> Feedback:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_attachment(self, item: FeedbackAttachment) -> FeedbackAttachment:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_history(self, item: FeedbackHistory) -> FeedbackHistory:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get(self, feedback_id: int, user_id: int | None = None) -> Feedback | None:
        statement = select(Feedback).where(Feedback.id == feedback_id)
        if user_id is not None:
            statement = statement.where(Feedback.user_id == user_id)
        return self.db.scalar(statement)

    def list(
        self,
        *,
        user_id: int | None = None,
        search: str | None = None,
        feedback_type: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        sort_by: str = "created_at",
        descending: bool = True,
    ) -> list[Feedback]:
        statement = select(Feedback)
        if user_id is not None:
            statement = statement.where(Feedback.user_id == user_id)
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(Feedback.title.ilike(pattern), Feedback.description.ilike(pattern))
            )
        for column, value in (
            (Feedback.feedback_type, feedback_type),
            (Feedback.priority, priority),
            (Feedback.status, status),
        ):
            if value is not None:
                statement = statement.where(column == value)
        order = self.SORT_FIELDS.get(sort_by, Feedback.created_at)
        statement = statement.order_by(desc(order) if descending else asc(order), Feedback.id)
        return list(self.db.scalars(statement))

    def attachments(self, feedback_id: int) -> list[FeedbackAttachment]:
        return list(
            self.db.scalars(
                select(FeedbackAttachment)
                .where(FeedbackAttachment.feedback_id == feedback_id)
                .order_by(FeedbackAttachment.id)
            )
        )

    def history(self, feedback_id: int) -> list[FeedbackHistory]:
        return list(
            self.db.scalars(
                select(FeedbackHistory)
                .where(FeedbackHistory.feedback_id == feedback_id)
                .order_by(FeedbackHistory.id)
            )
        )
