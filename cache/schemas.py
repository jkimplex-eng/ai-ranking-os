from typing import Any

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    key: str = Field(min_length=1, max_length=300)
    value: Any
    ttl_seconds: int = Field(default=300, ge=1, le=86400)
    tags: list[str] = Field(default_factory=list)


class CacheWarmRequest(BaseModel):
    entries: list[CacheEntry] = Field(max_length=1000)


class CacheInvalidate(BaseModel):
    key: str | None = None
    tag: str | None = None
