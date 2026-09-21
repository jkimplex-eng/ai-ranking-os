from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from closed_beta.models import BetaAccessStatus, SubscriptionStatus


class TariffRead(BaseModel):
    code: str
    name: str
    monthly_price_rub: int
    description: str
    limits: "BetaLimits"
    selectable: bool = True


class SubscriptionUpdate(BaseModel):
    plan_code: str = Field(min_length=1, max_length=40)
    status: SubscriptionStatus
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    payment_provider: str | None = Field(default=None, max_length=40)
    external_customer_id: str | None = Field(default=None, max_length=200)
    external_subscription_id: str | None = Field(default=None, max_length=200)
    apply_plan_limits: bool = True


class SubscriptionRead(BaseModel):
    plan_code: str
    plan_name: str
    status: SubscriptionStatus
    starts_at: datetime | None
    ends_at: datetime | None
    payment_provider: str | None
    external_customer_id: str | None
    external_subscription_id: str | None
    checkout_available: bool
    checkout_message: str


class BetaLimits(BaseModel):
    daily_research_limit: int = Field(default=10, ge=0, le=10_000)
    monthly_research_limit: int = Field(default=100, ge=0, le=100_000)
    max_projects: int = Field(default=10, ge=0, le=10_000)
    max_domains: int = Field(default=25, ge=0, le=100_000)
    max_organization_users: int = Field(default=5, ge=1, le=10_000)


class BetaUserUpdate(BaseModel):
    status: BetaAccessStatus | None = None
    limits: BetaLimits | None = None


class BetaUserRead(BaseModel):
    user_id: int
    email: str
    display_name: str
    is_active: bool
    status: BetaAccessStatus
    registered_at: datetime
    last_seen_at: datetime | None
    research_count: int
    limits: BetaLimits
    subscription: SubscriptionRead


class InvitationCreate(BaseModel):
    email: EmailStr
    expires_in_hours: int = Field(default=72, ge=1, le=720)
    role_id: int | None = Field(default=None, ge=1)


class InvitationRead(BaseModel):
    id: int
    email: str
    token_prefix: str
    expires_at: datetime
    role_id: int | None
    send_count: int
    revoked_at: datetime | None
    accepted_at: datetime | None
    created_at: datetime


class InvitationCreated(InvitationRead):
    token: str
    accept_path: str


class InvitationAccept(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=1024)


class InvitationAccepted(BaseModel):
    user_id: int
    email: str
    status: BetaAccessStatus
