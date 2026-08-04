import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CitationInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    authority: float = Field(default=0.5, ge=0, le=1)
    source: str | None = None


class ObservationInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = "unknown"
    mentioned: bool = True
    recommendation_position: int | None = Field(default=None, ge=1)
    citations: list[CitationInput] = Field(default_factory=list)
    entity_confidence: float = Field(default=0.5, ge=0, le=1)
    observed_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_task_201_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            raise ValueError("Each observation must be an object")
        data = dict(value)
        data.setdefault("model", data.get("model_name", data.get("provider", "unknown")))
        data.setdefault("mentioned", data.get("is_mentioned", data.get("found", True)))
        data.setdefault(
            "recommendation_position",
            data.get("position", data.get("rank")),
        )
        data.setdefault(
            "entity_confidence",
            data.get("confidence", data.get("extraction_confidence", 0.5)),
        )
        data.setdefault(
            "observed_at",
            data.get("timestamp", data.get("created_at")),
        )

        citations = data.get("citations", [])
        if isinstance(citations, int):
            citations = [{"authority": 0.5} for _ in range(max(0, citations))]
        elif isinstance(citations, list):
            citations = [
                {"authority": item} if isinstance(item, int | float) else item
                for item in citations
            ]
        data["citations"] = citations
        return data


class VisibilityInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    entity_id: str | None = Field(default=None, max_length=200)
    entity: str = Field(min_length=1, max_length=300)
    observations: list[ObservationInput] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def accept_task_201_shapes(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            raise ValueError("Visibility input must be an object")
        data = dict(value)
        extraction = data.get("entity_extraction_result")
        if isinstance(extraction, dict):
            data.setdefault(
                "entity",
                extraction.get("entity", extraction.get("name")),
            )
            data.setdefault(
                "entity_id",
                extraction.get("entity_id", extraction.get("id")),
            )

        if not data.get("entity"):
            data["entity"] = data.get("brand", data.get("entity_name"))

        if "observations" not in data:
            candidates: Any = None
            for key in ("responses", "model_results", "results"):
                if key in data:
                    candidates = data[key]
                    break
            if candidates is None and isinstance(extraction, dict):
                for key in ("observations", "responses", "model_results", "results", "mentions"):
                    if key in extraction:
                        candidates = extraction[key]
                        break
            if candidates is None and isinstance(extraction, list):
                candidates = extraction
            if candidates is None and any(
                key in data for key in ("model", "model_name", "mentioned", "is_mentioned")
            ):
                candidates = [data]
            data["observations"] = candidates
        return data

    @model_validator(mode="after")
    def derive_entity_id(self) -> "VisibilityInput":
        if self.entity_id is None:
            slug = re.sub(r"[^a-z0-9]+", "-", self.entity.lower()).strip("-")
            self.entity_id = slug or "entity"
        return self


class VisibilityBatchInput(BaseModel):
    items: list[VisibilityInput] = Field(min_length=1, max_length=100)


class VisibilityResult(BaseModel):
    entity_id: str
    entity: str
    visibility_score: float
    confidence: float
    metrics: dict[str, float]
    weights: dict[str, float]
    version: str
    calculated_at: datetime
