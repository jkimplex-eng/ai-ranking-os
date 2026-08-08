from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research.schemas import ResearchModelSelection, ResearchRead

PROMPT_CATEGORIES = {"Visibility", "Brand", "Product", "Competitor", "Reputation", "GEO"}


class PromptCreate(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,99}$")
    version: int = Field(default=1, ge=1)
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    category: str
    language: str = Field(default="en", min_length=2, max_length=16)
    variables: list[str] = Field(default_factory=list)
    template: str = Field(min_length=1)
    expected_output: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_contract(self) -> "PromptCreate":
        if self.category not in PROMPT_CATEGORIES:
            raise ValueError(f"Unsupported category: {self.category}")
        missing = [name for name in self.variables if "{" + name + "}" not in self.template]
        if missing:
            raise ValueError(f"Template misses variables: {', '.join(missing)}")
        return self


class PromptUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    language: str | None = Field(default=None, min_length=2, max_length=16)
    variables: list[str] | None = None
    template: str | None = Field(default=None, min_length=1)
    expected_output: dict[str, Any] | None = None
    tags: list[str] | None = None


class PromptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    version: int
    title: str
    description: str
    category: str
    language: str
    variables: list[str]
    template: str
    expected_output: dict[str, Any]
    tags: list[str]
    status: str
    active: bool
    created_at: datetime


class ResearchTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    version: int
    title: str
    description: str
    prompt_code: str
    pipeline: list[str]
    default_languages: list[str]
    default_regions: list[str]
    active: bool
    created_at: datetime


class WizardRequest(BaseModel):
    brand: str = Field(min_length=1, max_length=300)
    entity_id: UUID | None = None
    models: list[ResearchModelSelection] = Field(min_length=1, max_length=20)
    languages: list[str] = Field(default_factory=lambda: ["en"], min_length=1)
    regions: list[str] = Field(default_factory=lambda: ["GLOBAL"], min_length=1)
    prompt_code: str = "ai-visibility"
    research_template_code: str = "ai-visibility"
    variables: dict[str, str] = Field(default_factory=dict)


class WizardReview(BaseModel):
    valid: bool
    title: str
    prompt: str
    provider_models: list[str]
    languages: list[str]
    regions: list[str]
    pipeline: list[str]


class WizardRunResult(BaseModel):
    research: ResearchRead
    report_url: str
    report: dict[str, Any]
