from audit.ports import AuditWriter
from feedback_center.models import (
    Feedback,
    FeedbackAttachment,
    FeedbackHistory,
    FeedbackPriority,
    FeedbackStatus,
    FeedbackType,
)
from feedback_center.repository import FeedbackRepository
from feedback_center.schemas import (
    AttachmentRead,
    FeedbackAdminUpdate,
    FeedbackBulkUpdate,
    FeedbackCreate,
    FeedbackHistoryRead,
    FeedbackRead,
)


class FeedbackNotFoundError(LookupError):
    pass


class FeedbackService:
    def __init__(self, repository: FeedbackRepository, audit: AuditWriter) -> None:
        self.repository = repository
        self.audit = audit

    def _read(self, item: Feedback) -> FeedbackRead:
        return FeedbackRead(
            id=item.id,
            user_id=item.user_id,
            feedback_type=FeedbackType(item.feedback_type),
            priority=FeedbackPriority(item.priority),
            status=FeedbackStatus(item.status),
            title=item.title,
            description=item.description,
            project_id=item.project_id,
            research_id=item.research_id,
            report_id=item.report_id,
            organization_id=item.organization_id,
            attachments=[
                AttachmentRead(
                    id=row.id,
                    filename=row.filename,
                    content_type=row.content_type,
                    storage_key=row.storage_key,
                    size_bytes=row.size_bytes,
                    metadata=row.metadata_payload,
                    created_at=row.created_at,
                )
                for row in self.repository.attachments(item.id)
            ],
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def create(
        self, user_id: int, payload: FeedbackCreate, correlation_id: str
    ) -> FeedbackRead:
        values = payload.model_dump(exclude={"attachments"}, mode="json")
        item = self.repository.save(
            Feedback(user_id=user_id, status=FeedbackStatus.NEW.value, **values)
        )
        for attachment in payload.attachments:
            values = attachment.model_dump(exclude={"metadata"})
            self.repository.add_attachment(
                FeedbackAttachment(
                    feedback_id=item.id,
                    metadata_payload=attachment.metadata,
                    **values,
                )
            )
        self._history(item.id, str(user_id), "CREATED", None, self._state(item))
        self._audit(item, str(user_id), "created", correlation_id)
        return self._read(item)

    def list_user(self, user_id: int) -> list[FeedbackRead]:
        return [self._read(item) for item in self.repository.list(user_id=user_id)]

    def get_user(self, user_id: int, feedback_id: int) -> FeedbackRead:
        item = self.repository.get(feedback_id, user_id)
        if item is None:
            raise FeedbackNotFoundError("Feedback not found")
        return self._read(item)

    def admin_list(self, **filters) -> list[FeedbackRead]:
        return [self._read(item) for item in self.repository.list(**filters)]

    def update(
        self,
        feedback_id: int,
        payload: FeedbackAdminUpdate,
        actor_id: str,
        correlation_id: str,
    ) -> FeedbackRead:
        item = self.repository.get(feedback_id)
        if item is None:
            raise FeedbackNotFoundError("Feedback not found")
        old = self._state(item)
        for field, value in payload.model_dump(exclude_none=True, mode="json").items():
            setattr(item, field, value)
        item = self.repository.save(item)
        self._history(item.id, actor_id, "UPDATED", old, self._state(item))
        self._audit(item, actor_id, "updated", correlation_id, old)
        return self._read(item)

    def bulk(
        self, payload: FeedbackBulkUpdate, actor_id: str, correlation_id: str
    ) -> list[FeedbackRead]:
        update = FeedbackAdminUpdate(status=payload.status, priority=payload.priority)
        return [
            self.update(feedback_id, update, actor_id, correlation_id)
            for feedback_id in dict.fromkeys(payload.feedback_ids)
        ]

    def history(self, feedback_id: int) -> list[FeedbackHistoryRead]:
        if self.repository.get(feedback_id) is None:
            raise FeedbackNotFoundError("Feedback not found")
        return [
            FeedbackHistoryRead.model_validate(item, from_attributes=True)
            for item in self.repository.history(feedback_id)
        ]

    def _history(self, feedback_id, actor_id, action, old_state, new_state) -> None:
        self.repository.add_history(
            FeedbackHistory(
                feedback_id=feedback_id,
                actor_id=actor_id,
                action=action,
                old_state=old_state,
                new_state=new_state,
            )
        )

    @staticmethod
    def _state(item: Feedback) -> dict:
        return {"status": item.status, "priority": item.priority}

    def _audit(self, item, actor_id, action, correlation_id, old_state=None) -> None:
        self.audit.record(
            actor_id=actor_id,
            actor_type="user",
            action=f"feedback.{action}",
            category="feedback",
            resource="feedback",
            resource_id=str(item.id),
            correlation_id=correlation_id,
            old_state=old_state,
            new_state=self._state(item),
        )
