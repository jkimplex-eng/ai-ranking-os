from pydantic import BaseModel, Field


class EvaluationModel(BaseModel):
    provider: str
    model: str


class EvaluationRequest(BaseModel):
    models: list[EvaluationModel] = Field(min_length=1, max_length=20)
    tasks: list[str] = Field(default_factory=list)


class EvaluationScoreRead(BaseModel):
    provider: str
    model: str
    task: str
    score: float
    latency_ms: float
    version: str = "1.0"


class CapabilityMatrixRead(BaseModel):
    models: dict[str, dict[str, float]]
    tasks: list[str]
    version: str = "1.0"
