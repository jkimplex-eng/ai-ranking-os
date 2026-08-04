from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    owner_id: int = Field(gt=0)
    scopes: list[str] = Field(default_factory=list)
    rate_plan: str = Field(default="standard", max_length=50)
    expires_at: datetime | None = None


class ApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    owner_id: int
    prefix: str
    scopes: list[str]
    rate_plan: str
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyRead):
    secret: str


class ApiKeyValidation(BaseModel):
    credential: str
    required_scope: str | None = None


class ApiKeyValidationResult(BaseModel):
    valid: bool
    key_id: int | None = None
    owner_id: int | None = None
    scopes: list[str] = Field(default_factory=list)
    rate_plan: str | None = None
