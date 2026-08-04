from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DlqRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    queue: str
    payload: dict[str, Any]
    error: str
    attempts: int
    status: str
    created_at: datetime
