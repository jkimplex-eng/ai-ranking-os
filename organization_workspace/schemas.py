from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from organization_workspace.models import OrganizationRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,118}[a-z0-9]$")
    description: str = Field(default="", max_length=10_000)
    industry: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str = Field(default="UTC", max_length=64)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    logo_url: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str | None = Field(default=None, max_length=64)
    settings: dict | None = None
    limits: dict | None = None


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str
    logo_url: str | None
    industry: str | None
    country: str | None
    timezone: str
    settings: dict
    limits: dict
    role: OrganizationRole
    is_default: bool
    created_at: datetime


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    role: OrganizationRole
    is_default: bool
    joined_at: datetime


class MemberRoleUpdate(BaseModel):
    role: OrganizationRole


class InvitationCreate(BaseModel):
    email: EmailStr
    role: OrganizationRole = OrganizationRole.MEMBER
    expires_in_hours: int = Field(default=72, ge=1, le=720)


class InvitationRead(BaseModel):
    id: int
    organization_id: int
    email: EmailStr
    role: OrganizationRole
    expires_at: datetime
    token: str | None = None


class InvitationAccept(BaseModel):
    token: str = Field(min_length=32, max_length=200)


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int
    action: str
    entity_type: str | None
    entity_id: str | None
    metadata: dict
    created_at: datetime


class ProjectLink(BaseModel):
    project_id: int = Field(ge=1)
