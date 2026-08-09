from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkModel(BaseModel):
    provider: str
    model: str


class ModelBenchmarkRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=100_000)
    models: list[BenchmarkModel] = Field(min_length=1, max_length=20)
    iterations: int = Field(default=2, ge=1, le=10)


class ModelBenchmarkResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    provider: str
    model: str
    latency_ms: float
    cost_usd: float
    quality_score: float
    response_length: int
    stability_score: float


class ModelBenchmarkRead(BaseModel):
    id: int
    prompt: str
    iterations: int
    created_at: datetime
    results: list[ModelBenchmarkResultRead]
