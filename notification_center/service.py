from __future__ import annotations

from notification_center.models import Notification, NotificationDelivery, NotificationEventType
from notification_center.repository import NotificationRepository
from notification_center.schemas import DeliveryRead, NotificationRead


class NotificationNotFoundError(LookupError):
    pass


class NotificationService:
    CHANNELS = {"UI", "EMAIL", "TELEGRAM"}

    def __init__(self, repository: NotificationRepository) -> None:
        self.repository = repository

    def _read(self, item: Notification) -> NotificationRead:
        return NotificationRead(
            id=item.id,
            user_id=item.user_id,
            event_type=NotificationEventType(item.event_type),
            title=item.title,
            message=item.message,
            resource_type=item.resource_type,
            resource_id=item.resource_id,
            metadata=item.metadata_payload,
            is_read=item.is_read,
            created_at=item.created_at,
            deliveries=[
                DeliveryRead.model_validate(row, from_attributes=True)
                for row in self.repository.deliveries(item.id)
            ],
        )

    def emit(
        self,
        event_type: str,
        title: str,
        message: str,
        *,
        user_id: int = 1,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
        channels: tuple[str, ...] = ("UI",),
    ) -> NotificationRead:
        invalid = set(channels) - self.CHANNELS
        if invalid:
            raise ValueError(f"Unsupported notification channels: {sorted(invalid)}")
        item = self.repository.save(
            Notification(
                user_id=user_id,
                event_type=NotificationEventType(event_type).value,
                title=title,
                message=message,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata_payload=metadata or {},
            )
        )
        for channel in dict.fromkeys(channels):
            self.repository.add_delivery(
                NotificationDelivery(
                    notification_id=item.id,
                    channel=channel,
                    status="DELIVERED" if channel == "UI" else "PENDING",
                )
            )
        return self._read(item)

    def list(self, user_id: int, unread_only: bool = False) -> list[NotificationRead]:
        return [self._read(item) for item in self.repository.list(user_id, unread_only)]

    def mark_read(self, user_id: int, notification_id: int) -> NotificationRead:
        item = self.repository.get(user_id, notification_id)
        if item is None:
            raise NotificationNotFoundError("Notification not found")
        item.is_read = True
        return self._read(self.repository.save(item))
