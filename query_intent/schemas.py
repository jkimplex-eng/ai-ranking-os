from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IntentType(StrEnum):
    INFORMATIONAL = "INFORMATIONAL"
    NAVIGATIONAL = "NAVIGATIONAL"
    TRANSACTIONAL = "TRANSACTIONAL"
    COMMERCIAL_INVESTIGATION = "COMMERCIAL_INVESTIGATION"
    COMPARISON = "COMPARISON"
    RECOMMENDATION = "RECOMMENDATION"
    TROUBLESHOOTING = "TROUBLESHOOTING"
    HOW_TO = "HOW_TO"
    LOCAL = "LOCAL"
    RESEARCH = "RESEARCH"


INTENT_SUBTYPES: dict[IntentType, tuple[str, ...]] = {
    IntentType.INFORMATIONAL: ("DEFINITION", "FACTUAL", "EXPLANATORY"),
    IntentType.NAVIGATIONAL: ("WEBSITE", "LOGIN", "CONTACT"),
    IntentType.TRANSACTIONAL: ("PURCHASE", "BOOKING", "DOWNLOAD", "SIGNUP"),
    IntentType.COMMERCIAL_INVESTIGATION: ("PRICING", "FEATURES", "REVIEWS"),
    IntentType.COMPARISON: ("VERSUS", "ALTERNATIVES", "BENCHMARK"),
    IntentType.RECOMMENDATION: ("BEST_OF", "PERSONALIZED", "RANKED_LIST"),
    IntentType.TROUBLESHOOTING: ("ERROR", "DIAGNOSIS", "REPAIR"),
    IntentType.HOW_TO: ("INSTRUCTIONS", "SETUP", "TUTORIAL"),
    IntentType.LOCAL: ("NEARBY", "LOCAL_SERVICE", "DIRECTIONS"),
    IntentType.RESEARCH: ("ANALYSIS", "EVIDENCE", "STATISTICS", "REPORT"),
}


class IntentInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    request_id: str | None = Field(default=None, max_length=200)
    query: str = Field(min_length=1, max_length=10_000)

    @model_validator(mode="before")
    @classmethod
    def accept_raw_query(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"query": value}
        if not isinstance(value, dict):
            raise ValueError("Intent input must be a string or object")
        data = dict(value)
        if "query" not in data:
            data["query"] = data.get("text", data.get("prompt", data.get("request")))
        return data


class IntentBatchInput(BaseModel):
    items: list[IntentInput] = Field(min_length=1, max_length=100)


class LanguageResult(BaseModel):
    code: str
    confidence: float = Field(ge=0, le=1)


class ConstraintResult(BaseModel):
    constraint_type: str
    operator: str
    value: str | float | int
    confidence: float = Field(ge=0, le=1)


class QueryEntity(BaseModel):
    name: str
    entity_type: str
    confidence: float = Field(ge=0, le=1)
    knowledge_graph_id: str


class IntentCandidate(BaseModel):
    intent: IntentType
    subtype: str
    confidence: float = Field(ge=0, le=1)
    signals: list[str]


class ExpectedOutput(BaseModel):
    format: str
    fields: list[str]
    cardinality: str


class RoutingMetadata(BaseModel):
    strategy: str
    llm_fallback_required: bool
    rule_scores: dict[str, float]
    embedding_scores: dict[str, float]
    ensemble_scores: dict[str, float]


class IntentResult(BaseModel):
    request_id: str
    query: str
    language: LanguageResult
    primary_intent: IntentType
    intents: list[IntentCandidate]
    constraints: list[ConstraintResult]
    entities: list[QueryEntity]
    expected_output: ExpectedOutput
    confidence: float = Field(ge=0, le=1)
    routing: RoutingMetadata
    version: str = "1.0"
    classified_at: datetime

