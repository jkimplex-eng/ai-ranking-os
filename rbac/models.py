from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base

role_permissions = Table(
    "rbac_role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("rbac_roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id", ForeignKey("rbac_permissions.id", ondelete="CASCADE"), primary_key=True
    ),
)
role_inheritance = Table(
    "rbac_role_inheritance",
    Base.metadata,
    Column("role_id", ForeignKey("rbac_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("parent_role_id", ForeignKey("rbac_roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "rbac_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class Permission(Base):
    __tablename__ = "rbac_permissions"
    __table_args__ = (UniqueConstraint("resource", "action", "scope", name="uq_rbac_permission"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    scope: Mapped[str] = mapped_column(String(100), default="global", nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)


class UserRole(Base):
    __tablename__ = "rbac_user_roles"
    __table_args__ = (Index("ix_rbac_user_roles_user", "user_id"),)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("rbac_roles.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
