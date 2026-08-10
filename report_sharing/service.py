import hashlib
import secrets
from datetime import UTC, datetime

from audit.ports import AuditWriter
from authentication.security import Argon2PasswordHasher
from report_center.ports import ReportSource
from report_sharing.models import ReportShareLink, ReportShareView, ShareAccessMode
from report_sharing.repository import ShareRepository
from report_sharing.schemas import ShareCreate, ShareCreated, SharedReportRead, ShareRead


class ShareAccessError(LookupError):
    pass


class ShareService:
    def __init__(
        self,
        repository: ShareRepository,
        source: ReportSource,
        audit: AuditWriter,
    ) -> None:
        self.repository = repository
        self.source = source
        self.audit = audit
        self.passwords = Argon2PasswordHasher()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _read(self, link: ReportShareLink) -> ShareRead:
        return ShareRead.model_validate(
            link,
            from_attributes=True,
        ).model_copy(update={"view_count": self.repository.view_count(link.id)})

    def _create(
        self,
        research_id: int,
        payload: ShareCreate,
        actor_id: str,
        correlation_id: str,
        password_hash: str | None = None,
    ) -> ShareCreated:
        self.source.export_payload(research_id)
        if payload.expires_at is not None:
            expires = payload.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires <= datetime.now(UTC):
                raise ValueError("Share expiration must be in the future")
        token = secrets.token_urlsafe(32)
        link = self.repository.save(
            ReportShareLink(
                research_id=research_id,
                token_hash=self._hash_token(token),
                token_prefix=token[:12],
                access_mode=payload.access_mode.value,
                password_hash=password_hash
                or (self.passwords.hash(payload.password) if payload.password else None),
                expires_at=payload.expires_at,
                created_by=actor_id,
            )
        )
        self.audit.record(
            actor_id=actor_id,
            actor_type="user",
            action="report.share.created",
            category="reports",
            resource="report_share",
            resource_id=str(link.id),
            correlation_id=correlation_id,
            new_state={"research_id": research_id, "access_mode": link.access_mode},
        )
        read = self._read(link)
        return ShareCreated(
            **read.model_dump(), token=token, url_path=f"/shared/reports/{token}"
        )

    def create(
        self, research_id: int, payload: ShareCreate, actor_id: str, correlation_id: str
    ) -> ShareCreated:
        return self._create(research_id, payload, actor_id, correlation_id)

    def list(self, research_id: int) -> list[ShareRead]:
        return [self._read(link) for link in self.repository.list(research_id)]

    def revoke(self, share_id: int, actor_id: str, correlation_id: str) -> ShareRead:
        link = self.repository.get(share_id)
        if link is None:
            raise ShareAccessError("Share link not found")
        link.active = False
        link.revoked_at = datetime.now(UTC)
        self.repository.save(link)
        self.audit.record(
            actor_id=actor_id,
            actor_type="user",
            action="report.share.revoked",
            category="reports",
            resource="report_share",
            resource_id=str(link.id),
            correlation_id=correlation_id,
        )
        return self._read(link)

    def rotate(self, share_id: int, actor_id: str, correlation_id: str) -> ShareCreated:
        old = self.repository.get(share_id)
        if old is None:
            raise ShareAccessError("Share link not found")
        self.revoke(share_id, actor_id, correlation_id)
        return self._create(
            old.research_id,
            ShareCreate.model_construct(
                access_mode=ShareAccessMode(old.access_mode),
                expires_at=old.expires_at,
                password=None,
            ),
            actor_id,
            correlation_id,
            password_hash=old.password_hash,
        )

    def open(
        self,
        token: str,
        password: str | None,
        ip_address: str | None,
        user_agent: str | None,
        correlation_id: str,
    ) -> SharedReportRead:
        link = self.repository.by_token_hash(self._hash_token(token))
        now = datetime.now(UTC)
        if link is None or not link.active:
            raise ShareAccessError("Share link is unavailable")
        expires_at = link.expires_at
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= now:
                raise ShareAccessError("Share link has expired")
        if link.access_mode == ShareAccessMode.PRIVATE.value and (
            not password
            or not link.password_hash
            or not self.passwords.verify(link.password_hash, password)
        ):
            raise ShareAccessError("Share password is invalid")
        report = self.source.export_payload(link.research_id)
        self.repository.add_view(
            ReportShareView(
                share_id=link.id,
                ip_address=ip_address,
                user_agent=user_agent,
                correlation_id=correlation_id,
            )
        )
        self.audit.record(
            actor_id="anonymous",
            actor_type="external",
            action="report.share.viewed",
            category="reports",
            resource="report_share",
            resource_id=str(link.id),
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return SharedReportRead(report=report)
from __future__ import annotations
