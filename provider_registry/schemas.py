from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"


class ProviderCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9_-]+$")
    display_name: str = Field(min_length=1, max_length=200)
    capabilities: list[str] = Field(default_factory=list)
    pricing: dict[str, Any] = Field(default_factory=dict)
    context_window: int = Field(gt=0)
    vision: bool = False
    embeddings: bool = False
    reasoning: bool = False
    tools: bool = False
    json_mode: bool = False
    streaming: bool = False
    availability: ProviderAvailability = ProviderAvailability.AVAILABLE
    free_tier: bool = False
    priority: int = Field(default=100, ge=0, le=10_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    capabilities: list[str] | None = None
    pricing: dict[str, Any] | None = None
    context_window: int | None = Field(default=None, gt=0)
    vision: bool | None = None
    embeddings: bool | None = None
    reasoning: bool | None = None
    tools: bool | None = None
    json_mode: bool | None = None
    streaming: bool | None = None
    availability: ProviderAvailability | None = None
    free_tier: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=10_000)
    metadata: dict[str, Any] | None = None


class ProviderRead(ProviderCreate):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime


class CapabilityMatrix(BaseModel):
    capabilities: dict[str, list[str]]
    providers: int
