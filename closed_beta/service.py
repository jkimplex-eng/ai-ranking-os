import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from audit.ports import AuditWriter
from closed_beta.models import BetaAccessStatus, BetaInvitation, BetaUserProfile
from closed_beta.ports import IdentityPort, RolePort, UsagePort
from closed_beta.repository import BetaRepository
from closed_beta.schemas import (
    BetaLimits,
    BetaUserRead,
    BetaUserUpdate,
    InvitationAccept,
    InvitationAccepted,
    InvitationCreate,
    InvitationCreated,
    InvitationRead,
)


class BetaAdminError(ValueError):
    pass


class BetaNotFoundError(LookupError):
    pass


class ClosedBetaService:
    def __init__(
        self,
        repository: BetaRepository,
        identities: IdentityPort,
        usage: UsagePort,
        roles: RolePort,
        audit: AuditWriter,
    ) -> None:
        self.repository = repository
        self.identities = identities
        self.usage = usage
        self.roles = roles
        self.audit = audit

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _ensure_profile(self, user_id: int) -> BetaUserProfile:
        profile = self.repository.profile(user_id)
        if profile is None:
            profile = self.repository.save_profile(
                BetaUserProfile(user_id=user_id, status=BetaAccessStatus.WAITLIST.value)
            )
        return profile

    @staticmethod
    def _limits(profile: BetaUserProfile) -> BetaLimits:
        return BetaLimits(
            daily_research_limit=profile.daily_research_limit,
            monthly_research_limit=profile.monthly_research_limit,
            max_projects=profile.max_projects,
            max_domains=profile.max_domains,
            max_organization_users=profile.max_organization_users,
        )

    def users(
        self,
        search: str | None = None,
        status: BetaAccessStatus | None = None,
        active: bool | None = None,
    ) -> list[BetaUserRead]:
        facts = self.identities.users()
        profiles = self.repository.profiles([item.user_id for item in facts])
        counts = self.usage.research_counts([item.user_id for item in facts])
        result = []
        for fact in facts:
            profile = profiles.get(fact.user_id) or self._ensure_profile(fact.user_id)
            if search and search.casefold() not in (
                f"{fact.email} {fact.display_name}".casefold()
            ):
                continue
            if status and profile.status != status.value:
                continue
            if active is not None and fact.is_active != active:
                continue
            result.append(
                BetaUserRead(
                    **fact.__dict__,
                    status=BetaAccessStatus(profile.status),
                    research_count=counts.get(fact.user_id, 0),
                    limits=self._limits(profile),
                )
            )
        return result

    def update_user(
        self,
        user_id: int,
        payload: BetaUserUpdate,
        actor_id: str,
        correlation_id: str,
    ) -> BetaUserRead:
        facts = next((item for item in self.identities.users() if item.user_id == user_id), None)
        if facts is None:
            raise BetaNotFoundError("User not found")
        profile = self._ensure_profile(user_id)
        old = {"status": profile.status, "limits": self._limits(profile).model_dump()}
        if payload.status is not None:
            profile.status = payload.status.value
        if payload.limits is not None:
            for field, value in payload.limits.model_dump().items():
                setattr(profile, field, value)
        self.repository.save_profile(profile)
        self.audit.record(
            actor_id=actor_id,
            actor_type="user",
            action="beta.user.updated",
            category="closed_beta",
            resource="beta_user",
            resource_id=str(user_id),
            correlation_id=correlation_id,
            old_state=old,
            new_state={"status": profile.status, "limits": self._limits(profile).model_dump()},
        )
        return next(item for item in self.users() if item.user_id == user_id)

    @staticmethod
    def _invite_read(invite: BetaInvitation) -> InvitationRead:
        return InvitationRead.model_validate(invite, from_attributes=True)

    def create_invitation(
        self,
        payload: InvitationCreate,
        actor_id: str,
        correlation_id: str,
    ) -> InvitationCreated:
        if self.identities.exists(str(payload.email)):
            raise BetaAdminError("User already exists")
        token = secrets.token_urlsafe(32)
        invite = self.repository.save_invitation(
            BetaInvitation(
                email=str(payload.email).lower(),
                token_hash=self._hash(token),
                token_prefix=token[:12],
                expires_at=datetime.now(UTC) + timedelta(hours=payload.expires_in_hours),
                role_id=payload.role_id,
                invited_by=actor_id,
            )
        )
        self.audit.record(
            actor_id=actor_id,
            actor_type="user",
            action="beta.invitation.created",
            category="closed_beta",
            resource="beta_invitation",
            resource_id=str(invite.id),
            correlation_id=correlation_id,
            new_state={"email": invite.email, "expires_at": invite.expires_at.isoformat()},
        )
        read = self._invite_read(invite)
        return InvitationCreated(
            **read.model_dump(), token=token, accept_path=f"/beta/invitations/{token}/accept"
        )

    def invitations(self) -> list[InvitationRead]:
        return [self._invite_read(item) for item in self.repository.invitations()]

    def revoke_invitation(
        self, invitation_id: int, actor_id: str, correlation_id: str
    ) -> InvitationRead:
        invite = self.repository.invitation(invitation_id)
        if invite is None:
            raise BetaNotFoundError("Invitation not found")
        invite.revoked_at = datetime.now(UTC)
        self.repository.save_invitation(invite)
        self._audit_invite(invite, actor_id, correlation_id, "revoked")
        return self._invite_read(invite)

    def resend_invitation(
        self, invitation_id: int, actor_id: str, correlation_id: str
    ) -> InvitationCreated:
        invite = self.repository.invitation(invitation_id)
        if invite is None or invite.accepted_at is not None:
            raise BetaNotFoundError("Invitation not found")
        token = secrets.token_urlsafe(32)
        invite.token_hash = self._hash(token)
        invite.token_prefix = token[:12]
        invite.expires_at = datetime.now(UTC) + timedelta(hours=72)
        invite.revoked_at = None
        invite.send_count += 1
        self.repository.save_invitation(invite)
        self._audit_invite(invite, actor_id, correlation_id, "resent")
        read = self._invite_read(invite)
        return InvitationCreated(
            **read.model_dump(), token=token, accept_path=f"/beta/invitations/{token}/accept"
        )

    def _audit_invite(
        self, invite: BetaInvitation, actor_id: str, correlation_id: str, action: str
    ) -> None:
        self.audit.record(
            actor_id=actor_id,
            actor_type="user",
            action=f"beta.invitation.{action}",
            category="closed_beta",
            resource="beta_invitation",
            resource_id=str(invite.id),
            correlation_id=correlation_id,
        )

    def accept(self, token: str, payload: InvitationAccept) -> InvitationAccepted:
        invite = self.repository.invitation_by_hash(self._hash(token))
        now = datetime.now(UTC)
        if invite is None or invite.revoked_at or invite.accepted_at:
            raise BetaNotFoundError("Invitation is unavailable")
        expires = invite.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= now:
            raise BetaNotFoundError("Invitation has expired")
        user_id = self.identities.create(invite.email, payload.password, payload.display_name)
        profile = self.repository.save_profile(
            BetaUserProfile(user_id=user_id, status=BetaAccessStatus.ACTIVE.value)
        )
        if invite.role_id is not None:
            self.roles.assign(user_id, invite.role_id)
        invite.accepted_at = now
        self.repository.save_invitation(invite)
        self.audit.record(
            actor_id=str(user_id),
            actor_type="user",
            action="beta.invitation.accepted",
            category="closed_beta",
            resource="beta_invitation",
            resource_id=str(invite.id),
            correlation_id=secrets.token_hex(16),
        )
        return InvitationAccepted(
            user_id=user_id, email=invite.email, status=BetaAccessStatus(profile.status)
        )
