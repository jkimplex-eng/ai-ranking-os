from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from report_sharing.models import ShareAccessMode


class ShareCreate(BaseModel):
    access_mode: ShareAccessMode = ShareAccessMode.PUBLIC
    expires_at: datetime | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)

    @model_validator(mode="after")
    def private_requires_password(self):
        if self.access_mode is ShareAccessMode.PRIVATE and not self.password:
            raise ValueError("Private links require a password")
        return self


class ShareRead(BaseModel):
    id: int
    research_id: int
    access_mode: ShareAccessMode
    token_prefix: str
    active: bool
    expires_at: datetime | None
    created_at: datetime
    revoked_at: datetime | None
    view_count: int = 0


class ShareCreated(ShareRead):
    token: str
    url_path: str


class SharedReportRead(BaseModel):
    read_only: bool = True
    report: dict
