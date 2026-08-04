from pydantic import BaseModel, ConfigDict, Field


class PolicyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    algorithm: str = Field(pattern="^(token_bucket|sliding_window)$")
    subject_type: str = Field(pattern="^(user|api_key|ip|endpoint)$")
    endpoint: str = "*"
    limit: int = Field(gt=0)
    window_seconds: int = Field(gt=0)
    burst: int = Field(default=0, ge=0)
    enabled: bool = True


class PolicyRead(PolicyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RateCheck(BaseModel):
    policy_id: int
    subject: str


class RateDecisionRead(BaseModel):
    allowed: bool
    remaining: int
    retry_after_seconds: float
