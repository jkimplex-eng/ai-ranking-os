from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class RegisteredModel(Base):
    __tablename__ = "router_models"

    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    display_name: Mapped[str] = mapped_column(String(300))
    version: Mapped[str] = mapped_column(String(100), default="1.0")
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), index=True)
    tier: Mapped[str] = mapped_column(String(30), index=True)
    capabilities: Mapped[list[str]] = mapped_column(JSON)
    input_cost_per_million: Mapped[float] = mapped_column(Float)
    output_cost_per_million: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)
    tokens_per_second: Mapped[float] = mapped_column(Float, default=0)
    average_latency: Mapped[float] = mapped_column(Float, default=0)
    benchmark_score: Mapped[float] = mapped_column(Float, default=0)
    quality: Mapped[float] = mapped_column(Float)
    availability: Mapped[float] = mapped_column(Float)
    context_window: Mapped[int] = mapped_column(Integer)
    hallucination_rate: Mapped[float] = mapped_column(Float)
    domains: Mapped[list[str]] = mapped_column(JSON)
    languages: Mapped[list[str]] = mapped_column(JSON)
    region: Mapped[str] = mapped_column(String(20), default="GLOBAL", index=True)
    success_probability: Mapped[float] = mapped_column(Float, default=0.95)
    reasoning: Mapped[bool] = mapped_column(Boolean, default=False)
    multimodal: Mapped[bool] = mapped_column(Boolean, default=False)
    embeddings: Mapped[bool] = mapped_column(Boolean, default=False)
    json_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    tool_calling: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ModelVersionRecord(Base):
    __tablename__ = "router_model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[str] = mapped_column(String(200), index=True)
    version: Mapped[str] = mapped_column(String(100), index=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RoutingPolicy(Base):
    __tablename__ = "router_policies"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    execution_mode: Mapped[str] = mapped_column(String(30))
    top_k: Mapped[int] = mapped_column(Integer)
    weights: Mapped[dict[str, float]] = mapped_column(JSON)
    required_capabilities: Mapped[list[str]] = mapped_column(JSON)
    daily_budget_usd: Mapped[float | None] = mapped_column(Float)
    monthly_budget_usd: Mapped[float | None] = mapped_column(Float)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RouterHistory(Base):
    __tablename__ = "router_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correlation_id: Mapped[str] = mapped_column(String(200), index=True)
    query: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(50), index=True)
    policy_id: Mapped[str] = mapped_column(String(100), index=True)
    selected_models: Mapped[list[str]] = mapped_column(JSON)
    execution_mode: Mapped[str] = mapped_column(String(30))
    routing_scores: Mapped[dict[str, Any]] = mapped_column(JSON)
    estimated_cost_usd: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)
    fallback_count: Mapped[int] = mapped_column(Integer)
    budget_downgraded: Mapped[bool] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RouterCostLog(Base):
    __tablename__ = "router_cost_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correlation_id: Mapped[str] = mapped_column(String(200), index=True)
    model_id: Mapped[str] = mapped_column(String(200), index=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float)
    cost_type: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class CircuitBreakerRecord(Base):
    __tablename__ = "router_circuit_breakers"

    model_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    state: Mapped[str] = mapped_column(String(30), index=True)
    failure_count: Mapped[int] = mapped_column(Integer)
    success_count: Mapped[int] = mapped_column(Integer)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
