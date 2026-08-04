from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExecutionMode(StrEnum):
    SINGLE = "SINGLE"
    PARALLEL = "PARALLEL"
    ENSEMBLE = "ENSEMBLE"
    CONSENSUS = "CONSENSUS"
    FALLBACK = "FALLBACK"


class ExecutorState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class StepState(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED = "SKIPPED"


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="allow")

    step_id: str
    provider: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    max_retries: int = Field(default=2, ge=0, le=3)
    retry_base_seconds: float = Field(default=0.1, ge=0, le=30)
    required: bool = True

    @model_validator(mode="before")
    @classmethod
    def accept_provider_shorthand(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"step_id": value, "provider": value}
        if not isinstance(value, dict):
            raise ValueError("Plan step must be a provider name or object")
        data = dict(value)
        data.setdefault("provider", data.get("provider_id", data.get("model", data.get("agent"))))
        data.setdefault("step_id", data.get("id", data.get("route_id", data.get("provider"))))
        data.setdefault("payload", data.get("input", data.get("request", {})))
        data.setdefault("timeout_seconds", data.get("timeout", 30.0))
        data.setdefault("max_retries", data.get("retries", 2))
        return data


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    plan_id: str | None = Field(default=None, max_length=200)
    request_id: str | None = Field(default=None, max_length=200)
    mode: ExecutionMode = ExecutionMode.SINGLE
    steps: list[PlanStep] = Field(min_length=1, max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_router_contract_shapes(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            raise ValueError("Execution Plan must be an object")
        data = dict(value)
        nested = data.get("execution_plan")
        if isinstance(nested, dict):
            outer = {key: item for key, item in data.items() if key != "execution_plan"}
            data = {**nested, **outer}
        data.setdefault(
            "mode",
            data.get("execution_mode", data.get("strategy", data.get("type", "SINGLE"))),
        )
        if isinstance(data.get("mode"), str):
            data["mode"] = data["mode"].upper()

        if "steps" not in data:
            candidates = data.get("routes", data.get("providers"))
            if isinstance(candidates, dict):
                candidates = [
                    {"provider": provider, **(settings if isinstance(settings, dict) else {})}
                    for provider, settings in candidates.items()
                ]
            data["steps"] = candidates
        if isinstance(data.get("steps"), list):
            data["steps"] = [
                {"step_id": f"step-{index}", "provider": item}
                if isinstance(item, str)
                else {"step_id": f"step-{index}", **item}
                if isinstance(item, dict) and not item.get("step_id") and not item.get("id")
                else item
                for index, item in enumerate(data["steps"], start=1)
            ]
        return data

    @model_validator(mode="after")
    def derive_plan_id(self) -> "ExecutionPlan":
        if self.plan_id is None:
            self.plan_id = str(uuid4())
        return self


class StepResult(BaseModel):
    step_id: str
    provider: str
    state: StepState
    attempts: int
    latency_ms: int
    output: Any = None
    error: str | None = None


class ExecutorResult(BaseModel):
    execution_id: str
    plan_id: str
    request_id: str | None
    mode: ExecutionMode
    state: ExecutorState
    results: list[StepResult]
    output: Any = None
    error: str | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    telemetry: dict[str, Any]
    version: str = "1.0"


class CancellationResult(BaseModel):
    execution_id: str
    state: ExecutorState
