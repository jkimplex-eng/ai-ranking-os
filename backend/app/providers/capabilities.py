from enum import StrEnum

from pydantic import BaseModel, Field


class Region(StrEnum):
    GLOBAL = "GLOBAL"
    RUSSIA = "RUSSIA"


class Capability(StrEnum):
    CHAT = "chat"
    STREAMING = "streaming"
    FUNCTION_CALLING = "function_calling"
    JSON_MODE = "json_mode"
    VISION = "vision"
    IMAGE_GENERATION = "image_generation"
    EMBEDDINGS = "embeddings"
    TOOL_USE = "tool_use"
    RESEARCH = "research"
    CITATIONS = "citations"


class ModelCapabilities(BaseModel):
    context_window: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    temperature_min: float = 0
    temperature_max: float = 2
    features: set[Capability] = Field(default_factory=set)

    def supports(self, capability: Capability | str) -> bool:
        return Capability(capability) in self.features

