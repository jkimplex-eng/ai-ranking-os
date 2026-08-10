from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class UserWorkspace(Base):
    __tablename__ = "user_workspaces"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_workspaces_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class Project(Base):
    __tablename__ = "workspace_projects"
    __table_args__ = (
        Index("ix_workspace_projects_workspace_updated", "workspace_id", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("user_workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class ProjectCompetitor(Base):
    __tablename__ = "project_competitors"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_competitors_name"),
        Index("ix_project_competitors_project_active", "project_id", "active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("workspace_projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domains: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    brands: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class ProjectDomain(Base):
    __tablename__ = "project_domains"
    __table_args__ = (
        UniqueConstraint("project_id", "hostname", name="uq_project_domains_hostname"),
        Index("ix_project_domains_project", "project_id", "active"),
        Index(
            "uq_project_domains_primary",
            "project_id",
            unique=True,
            postgresql_where=text("is_primary = true"),
            sqlite_where=text("is_primary = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("workspace_projects.id", ondelete="CASCADE"), nullable=False
    )
    hostname: Mapped[str] = mapped_column(String(253), nullable=False)
    display_name: Mapped[str] = mapped_column(String(253), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    brands: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class SavedResearchConfiguration(Base):
    __tablename__ = "saved_research_configurations"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_saved_research_config_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("workspace_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    template_code: Mapped[str] = mapped_column(String(100), nullable=False)
    routing_profile: Mapped[str] = mapped_column(String(30), nullable=False)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    regions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    prompt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schedule_hint: Mapped[str | None] = mapped_column(String(100))
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class BulkResearchRun(Base):
    __tablename__ = "bulk_research_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("workspace_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    template_code: Mapped[str] = mapped_column(String(100), nullable=False)
    routing_profile: Mapped[str] = mapped_column(String(30), nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class BulkResearchItem(Base):
    __tablename__ = "bulk_research_items"
    __table_args__ = (
        UniqueConstraint("bulk_run_id", "brand", name="uq_bulk_research_item_brand"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bulk_run_id: Mapped[int] = mapped_column(
        ForeignKey("bulk_research_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    brand: Mapped[str] = mapped_column(String(200), nullable=False)
    domain_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_domains.id", ondelete="SET NULL"), nullable=True
    )
    research_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
