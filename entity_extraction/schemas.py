from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from entity_extraction.entity_types import EntityType


class ExtractionInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    response_id: str | None = Field(default=None, max_length=200)
    raw_response: Any
    model: str | None = Field(default=None, max_length=100)

    @model_validator(mode="before")
    @classmethod
    def accept_raw_and_aliased_inputs(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return {"raw_response": value}
        data = dict(value)
        if "raw_response" not in data:
            for key in ("response", "content", "text", "output"):
                if key in data:
                    data["raw_response"] = data[key]
                    break
        if "raw_response" not in data:
            data["raw_response"] = value
        return data


class ExtractionBatchInput(BaseModel):
    items: list[ExtractionInput] = Field(min_length=1, max_length=100)


class ExtractedEntity(BaseModel):
    temp_id: str
    name: str
    entity_type: EntityType
    confidence: float = Field(ge=0, le=1)
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    aliases: list[str] = Field(default_factory=list)
    knowledge_graph_id: str | None = None


class ExtractedRelation(BaseModel):
    relation_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: Any
    confidence: float = Field(ge=0, le=1)


class EntityResult(BaseModel):
    entity_id: str
    name: str
    canonical_name: str
    entity_type: EntityType
    confidence: float = Field(ge=0, le=1)
    aliases: list[str]
    knowledge_graph_id: str


class RelationResult(BaseModel):
    relation_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    confidence: float = Field(ge=0, le=1)


class ResolutionLog(BaseModel):
    stage: str
    action: str
    details: dict[str, Any]


class ExtractionResult(BaseModel):
    response_id: str
    entities: list[EntityResult]
    relations: list[RelationResult]
    resolution_logs: list[ResolutionLog]
    version: str = "1.0"
    processed_at: datetime

