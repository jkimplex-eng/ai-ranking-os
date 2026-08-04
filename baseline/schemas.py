from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from baseline.models import BaselineUpdatePolicy, RegressionSeverity


class RegressionThresholds(BaseModel):
    minor: float = Field(default=5, ge=0, le=100)
    moderate: float = Field(default=10, ge=0, le=100)
    major: float = Field(default=20, ge=0, le=100)
    critical: float = Field(default=30, ge=0, le=100)

    @model_validator(mode="after")
    def ordered(self) -> "RegressionThresholds":
        if not self.minor <= self.moderate <= self.major <= self.critical:
            raise ValueError("thresholds must be ordered minor <= moderate <= major <= critical")
        return self


class BaselineCreate(BaseModel):
    research_id: int | None = Field(default=None, ge=1)
    update_policy: BaselineUpdatePolicy = BaselineUpdatePolicy.MANUAL
    thresholds: RegressionThresholds = Field(default_factory=RegressionThresholds)


class BaselineSnapshotRead(BaseModel):
    id: int
    research_id: int
    metrics: dict[str, float]
    reason: str
    algorithm_version: str
    created_at: datetime


class BaselineRead(BaseModel):
    id: int
    entity_id: UUID
    research_id: int
    update_policy: BaselineUpdatePolicy
    thresholds: RegressionThresholds
    algorithm_version: str
    created_at: datetime
    updated_at: datetime
    snapshots: list[BaselineSnapshotRead]


class RegressionEventRead(BaseModel):
    id: int
    metric: str
    baseline_value: float
    current_value: float
    delta: float
    severity: RegressionSeverity
    algorithm_version: str
    created_at: datetime


class EvaluationResult(BaseModel):
    entity_id: UUID
    baseline_snapshot_id: int
    baseline_research_id: int
    current_research_id: int
    algorithm_version: str
    baseline_updated: bool
    regressions: list[RegressionEventRead]
