from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.llm_router.schemas import RoutingProfile
from research.schemas import ResearchModelSelection, ResearchRead

PROMPT_CATEGORIES = {"Visibility", "Brand", "Product", "Competitor", "Reputation", "GEO"}
RESEARCH_TYPES = {
    "BRAND_VISIBILITY",
    "COMPETITOR_COMPARISON",
    "GEO_AUDIT",
    "AI_RECOMMENDATION_AUDIT",
    "CONTENT_AUDIT",
    "WEBSITE_AUDIT",
    "PRODUCT_AUDIT",
}


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
    research_type: str
    prompt_code: str
    pipeline: list[str]
    default_languages: list[str]
    default_regions: list[str]
    configuration: dict[str, Any]
    active: bool
    created_at: datetime


class ResearchTemplateCreate(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,99}$")
    version: int = Field(default=1, ge=1)
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    research_type: str
    prompt_code: str = Field(min_length=1, max_length=100)
    pipeline: list[str] = Field(min_length=1)
    default_languages: list[str] = Field(default_factory=lambda: ["en"])
    default_regions: list[str] = Field(default_factory=lambda: ["GLOBAL"])
    configuration: dict[str, Any] = Field(default_factory=dict)
    active: bool = True

    @model_validator(mode="after")
    def valid_type(self) -> "ResearchTemplateCreate":
        if self.research_type not in RESEARCH_TYPES:
            raise ValueError(f"Unsupported research type: {self.research_type}")
        return self


class ResearchTemplateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    research_type: str | None = None
    prompt_code: str | None = Field(default=None, min_length=1, max_length=100)
    pipeline: list[str] | None = Field(default=None, min_length=1)
    default_languages: list[str] | None = None
    default_regions: list[str] | None = None
    configuration: dict[str, Any] | None = None
    active: bool | None = None


class WizardRequest(BaseModel):
    brand: str = Field(min_length=1, max_length=300)
    website_url: str = Field(min_length=4, max_length=2000)
    entity_id: UUID | None = None
    models: list[ResearchModelSelection] = Field(default_factory=list, max_length=20)
    routing_profile: RoutingProfile = RoutingProfile.BALANCED
    languages: list[str] = Field(default_factory=lambda: ["en"], min_length=1)
    regions: list[str] = Field(default_factory=lambda: ["GLOBAL"], min_length=1)
    prompt_code: str = "ai-visibility"
    research_template_code: str = "ai-visibility"
    research_scope: str = Field(
        default="SELECTED",
        pattern=r"^(ALL|SELECTED|RUSSIAN|COMMERCIAL|FREE|CONSENSUS|COMPARE)$",
    )
    research_profile: str = Field(
        default="UNIVERSAL",
        pattern=r"^(GEO|ECOMMERCE|MEDICAL|BEAUTY|ENTERPRISE|UNIVERSAL)$",
    )
    variables: dict[str, str] = Field(default_factory=dict)
    brand_profile: dict[str, Any] | None = None
    competitors: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    custom_queries: list[str] = Field(default_factory=list, max_length=60)

    @field_validator("custom_queries")
    @classmethod
    def validate_custom_queries(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if any(len(value) < 12 or len(value) > 500 for value in cleaned):
            raise ValueError("Каждый пользовательский запрос должен содержать 12–500 символов")
        return cleaned


class BrandProfileRequest(BaseModel):
    brand: str = Field(min_length=1, max_length=300)
    website_url: str = Field(min_length=4, max_length=2000)


class BrandProfileRead(BaseModel):
    version: str
    brand: str
    website_url: str
    pages_analyzed: int
    evidence_urls: list[str]
    description: str
    categories: list[str]
    products: list[dict[str, Any]]
    attributes: list[str]
    confidence: float
    limitations: list[str]


class WizardReview(BaseModel):
    valid: bool
    title: str
    prompt: str
    provider_models: list[str]
    languages: list[str]
    regions: list[str]
    pipeline: list[str]
    estimated_cost_usd: float = 0
    estimated_time_ms: float = 0
    selected_models: list[str] = Field(default_factory=list)
    query_catalog: list[dict[str, str]] = Field(default_factory=list)
    task_count: int = 0
    brand_profile: BrandProfileRead
    competitor_profiles: list[BrandProfileRead] = Field(default_factory=list)


class WizardRunResult(BaseModel):
    research: ResearchRead
    report_url: str
    report: dict[str, Any]
