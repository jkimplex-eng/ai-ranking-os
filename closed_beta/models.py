from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class BetaAccessStatus(StrEnum):
    WAITLIST = "WAITLIST"
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class BetaUserProfile(Base):
    __tablename__ = "beta_user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITLIST")
    daily_research_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    monthly_research_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_projects: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_domains: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    max_organization_users: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class BetaInvitation(Base):
    __tablename__ = "beta_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    role_id: Mapped[int | None] = mapped_column(Integer)
    invited_by: Mapped[str] = mapped_column(String(100), nullable=False)
    send_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
