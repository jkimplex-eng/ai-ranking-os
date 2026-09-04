from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PromptTemplate(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    query_type: str = Field(pattern="^(CATEGORY|COMPARATIVE|USE_CASE|BRANDED)$")
    template: str = Field(min_length=3, max_length=1000)

    @field_validator("template")
    @classmethod
    def validate_template(cls, value: str) -> str:
        if "{" not in value or "}" not in value:
            raise ValueError("template must contain at least one {variable}")
        return value


class PromptSetCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=100)
    language: str = Field(min_length=2, max_length=16)
    region: str = Field(min_length=2, max_length=16)
    templates: list[PromptTemplate] = Field(min_length=1, max_length=500)


class PromptInstanceRead(ApiModel):
    id: UUID
    stable_key: str
    text: str
    query_type: str
    variables: dict
    position: int
    created_at: datetime


class PromptSetRead(ApiModel):
    id: UUID
    code: str
    version: int
    name: str
    category: str
    language: str
    region: str
    templates: list[dict]
    fingerprint: str
    frozen: bool
    active: bool
    created_at: datetime
    instances: list[PromptInstanceRead] = Field(default_factory=list)


class FanOutRequest(BaseModel):
    variables: dict[str, str | list[str]]


class FanOutResult(BaseModel):
    prompt_set_id: UUID
    fingerprint: str
    instances: list[PromptInstanceRead]
