from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class ResearchStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class ResearchTaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ResponseProcessingStatus(StrEnum):
    NORMALIZED = "NORMALIZED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class ResearchJobState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


research_status_type = Enum(
    ResearchStatus,
    name="research_status",
    native_enum=False,
    validate_strings=True,
    length=20,
)
research_task_status_type = Enum(
    ResearchTaskStatus,
    name="research_task_status",
    native_enum=False,
    validate_strings=True,
    length=20,
)
response_processing_status_type = Enum(
    ResponseProcessingStatus,
    name="response_processing_status",
    native_enum=False,
    validate_strings=True,
    length=20,
)


class Research(Base):
    __tablename__ = "researches"
    __table_args__ = (
        Index("ix_researches_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspace_projects.id", ondelete="SET NULL"), index=True
    )
    domain_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_domains.id", ondelete="SET NULL"), index=True
    )
    entity_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    objective: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ResearchStatus] = mapped_column(
        research_status_type,
        default=ResearchStatus.DRAFT,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    failed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    progress_percent: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    tasks: Mapped[list["ResearchTask"]] = relationship(
        back_populates="research",
        cascade="all, delete-orphan",
    )
    scores: Mapped[list["ResearchScore"]] = relationship(
        back_populates="research",
        cascade="all, delete-orphan",
    )


class ResearchTask(Base):
    __tablename__ = "research_tasks"
    __table_args__ = (
        Index("ix_research_tasks_research_id_status", "research_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"),
    )
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[ResearchTaskStatus] = mapped_column(
        research_task_status_type,
        default=ResearchTaskStatus.PENDING,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(200))
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    decision_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        index=True,
    )
    execution_id: Mapped[int | None] = mapped_column(
        ForeignKey("executions.id", ondelete="SET NULL"),
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    research: Mapped[Research] = relationship(back_populates="tasks")
    responses: Mapped[list["Response"]] = relationship(
        back_populates="research_task",
        cascade="all, delete-orphan",
    )


class ResearchJob(Base):
    __tablename__ = "research_jobs"
    __table_args__ = (Index("ix_research_jobs_state_created", "state", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"), index=True
    )
    state: Mapped[str] = mapped_column(String(30), default=ResearchJobState.PENDING, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Response(Base):
    __tablename__ = "research_responses"
    __table_args__ = (
        Index(
            "ix_research_responses_task_created_at",
            "research_task_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_task_id: Mapped[int] = mapped_column(
        ForeignKey("research_tasks.id", ondelete="CASCADE"),
    )
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    prompt: Mapped[str] = mapped_column(Text, default="")
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    normalized_response: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(default=0.0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[ResponseProcessingStatus] = mapped_column(
        response_processing_status_type,
        default=ResponseProcessingStatus.NORMALIZED,
    )
    processing_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    finished_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    research_task: Mapped[ResearchTask] = relationship(back_populates="responses")
    extracted_entities: Mapped[list["ExtractedEntity"]] = relationship(
        back_populates="response",
        cascade="all, delete-orphan",
    )
    extracted_citations: Mapped[list["ExtractedCitation"]] = relationship(
        back_populates="response",
        cascade="all, delete-orphan",
    )
    extracted_recommendations: Mapped[list["ExtractedRecommendation"]] = relationship(
        back_populates="response",
        cascade="all, delete-orphan",
    )


class ExtractedEntity(Base):
    __tablename__ = "research_extracted_entities"
    __table_args__ = (
        Index("ix_research_entities_response_type", "response_id", "entity_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("research_responses.id", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(String(500))
    canonical_name: Mapped[str] = mapped_column(String(500))
    entity_type: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(default=0.0)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    knowledge_graph_id: Mapped[str | None] = mapped_column(String(100))
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    response: Mapped[Response] = relationship(back_populates="extracted_entities")


class ExtractedCitation(Base):
    __tablename__ = "research_extracted_citations"
    __table_args__ = (Index("ix_research_citations_response", "response_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("research_responses.id", ondelete="CASCADE"),
    )
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str | None] = mapped_column(String(300))
    excerpt: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    response: Mapped[Response] = relationship(back_populates="extracted_citations")


class ExtractedRecommendation(Base):
    __tablename__ = "research_extracted_recommendations"
    __table_args__ = (Index("ix_research_recommendations_response", "response_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("research_responses.id", ondelete="CASCADE"),
    )
    content: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(default=0.0)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    response: Mapped[Response] = relationship(
        back_populates="extracted_recommendations"
    )


class ResearchScore(Base):
    __tablename__ = "research_scores"
    __table_args__ = (
        Index(
            "uq_research_scores_research_version",
            "research_id",
            "version",
            unique=True,
        ),
        Index("ix_research_scores_calculated_at", "calculated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"),
    )
    mention_score: Mapped[float] = mapped_column()
    recommendation_score: Mapped[float] = mapped_column()
    citation_score: Mapped[float] = mapped_column()
    coverage_score: Mapped[float] = mapped_column()
    confidence_score: Mapped[float] = mapped_column()
    visibility_score: Mapped[float] = mapped_column()
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(50))
    research: Mapped[Research] = relationship(back_populates="scores")
