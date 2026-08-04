from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from alert.models import AlertSeverity, AlertType


class AlertEventRead(BaseModel):
    id: int
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class AlertRead(BaseModel):
    id: int
    entity_id: UUID
    rule_code: str
    rule_version: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    previous_value: float | None
    current_value: float | None
    context: dict[str, Any]
    detected_at: datetime
    events: list[AlertEventRead]

