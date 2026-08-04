from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: str
    actor_type: str
    action: str
    category: str
    resource: str
    resource_id: str | None
    ip_address: str | None
    user_agent: str | None
    old_state: dict[str, Any] | None
    new_state: dict[str, Any] | None
    correlation_id: str
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEventRead]
    total: int
    page: int
    page_size: int
