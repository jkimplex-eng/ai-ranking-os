from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ModelPrice(BaseModel):
    provider: str
    model: str
    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)
    currency: str = "USD"

    def estimate(self, prompt_tokens: int, completion_tokens: int) -> float:
        return round(
            (
                prompt_tokens * self.input_per_million
                + completion_tokens * self.output_per_million
            )
            / 1_000_000,
            8,
        )


class UsageCost(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    currency: str
    provider: str
    model: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

