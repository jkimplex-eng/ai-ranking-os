from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{1,79}$")
    name: str = Field(min_length=2, max_length=150)
    description: str = Field(default="", max_length=500)
    parent_role_ids: list[int] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    parent_role_ids: list[int] | None = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    description: str
    is_system: bool
    parent_role_ids: list[int] = Field(default_factory=list)
    permission_ids: list[int] = Field(default_factory=list)


class PermissionCreate(BaseModel):
    resource: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=80)
    scope: str = Field(default="global", min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class PermissionRead(PermissionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RolePermissionChange(BaseModel):
    permission_id: int = Field(gt=0)


class UserRoleAssignment(BaseModel):
    role_id: int = Field(gt=0)


class AccessCheck(BaseModel):
    user_id: int = Field(gt=0)
    resource: str
    action: str
    scope: str = "global"


class AccessDecision(BaseModel):
    allowed: bool
    effective_role_ids: list[int]
