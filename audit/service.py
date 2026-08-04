import csv
import io
from typing import Any

from audit.models import AuditEvent
from audit.repository import AuditRepository
from audit.schemas import AuditEventRead, AuditPage


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    def record(self, **values: Any) -> AuditEventRead:
        return AuditEventRead.model_validate(self.repository.append(AuditEvent(**values)))

    def search(self, **filters) -> AuditPage:
        rows, total = self.repository.search(**filters)
        return AuditPage(
            items=[AuditEventRead.model_validate(x) for x in rows],
            total=total,
            page=filters.get("page", 1),
            page_size=filters.get("page_size", 50),
        )

    def export_csv(self, **filters):
        page = self.search(**filters)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "timestamp",
                "actor",
                "action",
                "category",
                "resource",
                "resource_id",
                "correlation_id",
            ]
        )
        for item in page.items:
            writer.writerow(
                [
                    item.id,
                    item.created_at.isoformat(),
                    item.actor_id,
                    item.action,
                    item.category,
                    item.resource,
                    item.resource_id,
                    item.correlation_id,
                ]
            )
        yield output.getvalue()
