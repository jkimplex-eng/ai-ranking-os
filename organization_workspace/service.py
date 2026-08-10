import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from organization_workspace.models import (
    Organization,
    OrganizationActivity,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationProject,
    OrganizationRole,
)
from organization_workspace.repository import OrganizationRepository
from organization_workspace.schemas import (
    ActivityRead,
    InvitationCreate,
    InvitationRead,
    MemberRead,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)


class OrganizationError(ValueError):
    pass


class OrganizationService:
    ADMIN_ROLES = {OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value}

    def __init__(self, repository: OrganizationRepository) -> None:
        self.repository = repository

    def _membership(self, organization_id: int, user_id: int, admin: bool = False):
        member = self.repository.member(organization_id, user_id)
        if member is None or (admin and member.role not in self.ADMIN_ROLES):
            raise OrganizationError("Organization not found")
        return member

    @staticmethod
    def _read(org, member):
        return OrganizationRead(
            **{
                column.name: getattr(org, column.name)
                for column in org.__table__.columns
                if column.name not in {"id"}
            },
            id=org.id,
            role=member.role,
            is_default=member.is_default,
        )

    def _activity(
        self,
        organization_id: int,
        actor_id: int,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict | None = None,
    ):
        self.repository.save(
            OrganizationActivity(
                organization_id=organization_id,
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata_payload=metadata or {},
            )
        )

    def create(self, user_id: int, payload: OrganizationCreate):
        org = self.repository.save(
            Organization(
                **payload.model_dump(),
                settings={},
                limits={"monthly_research": 100, "members": 5, "projects": 10},
            )
        )
        default = not self.repository.organizations(user_id)
        member = self.repository.save(
            OrganizationMember(
                organization_id=org.id, user_id=user_id, role="OWNER", is_default=default
            )
        )
        self._activity(org.id, user_id, "ORGANIZATION_CREATED", "organization", str(org.id))
        return self._read(org, member)

    def list(self, user_id: int):
        return [self._read(org, member) for org, member in self.repository.organizations(user_id)]

    def update(self, organization_id: int, user_id: int, payload: OrganizationUpdate):
        member = self._membership(organization_id, user_id, True)
        org = self.repository.organization(organization_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(org, key, value)
        self.repository.save(org)
        self._activity(organization_id, user_id, "ORGANIZATION_UPDATED")
        return self._read(org, member)

    def switch(self, organization_id: int, user_id: int):
        member = self._membership(organization_id, user_id)
        self.repository.clear_default(user_id)
        member.is_default = True
        self.repository.save(member)
        self._activity(organization_id, user_id, "ORGANIZATION_SWITCHED")
        return self._read(self.repository.organization(organization_id), member)

    def members(self, organization_id: int, user_id: int):
        self._membership(organization_id, user_id)
        return [
            MemberRead.model_validate(item, from_attributes=True)
            for item in self.repository.members(organization_id)
        ]

    def update_role(
        self, organization_id: int, actor_id: int, member_id: int, role: OrganizationRole
    ):
        self._membership(organization_id, actor_id, True)
        member = next(
            (item for item in self.repository.members(organization_id) if item.id == member_id),
            None,
        )
        if member is None or member.role == "OWNER":
            raise OrganizationError("Member not found or owner role is immutable")
        member.role = role.value
        self.repository.save(member)
        self._activity(
            organization_id,
            actor_id,
            "ROLE_CHANGED",
            "member",
            str(member.id),
            {"role": role.value},
        )
        return MemberRead.model_validate(member, from_attributes=True)

    def remove_member(self, organization_id: int, actor_id: int, member_id: int):
        self._membership(organization_id, actor_id, True)
        member = next(
            (item for item in self.repository.members(organization_id) if item.id == member_id),
            None,
        )
        if member is None or member.role == "OWNER":
            raise OrganizationError("Member not found or owner cannot be removed")
        self.repository.remove_member(member)
        self._activity(organization_id, actor_id, "MEMBER_REMOVED", "member", str(member_id))

    def invite(self, organization_id: int, actor_id: int, payload: InvitationCreate):
        self._membership(organization_id, actor_id, True)
        token = secrets.token_urlsafe(32)
        item = self.repository.save(
            OrganizationInvitation(
                organization_id=organization_id,
                email=str(payload.email),
                role=payload.role.value,
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                expires_at=datetime.now(UTC) + timedelta(hours=payload.expires_in_hours),
                invited_by=actor_id,
            )
        )
        self._activity(
            organization_id,
            actor_id,
            "MEMBER_INVITED",
            "invitation",
            str(item.id),
            {"email": str(payload.email)},
        )
        return InvitationRead(
            id=item.id,
            organization_id=organization_id,
            email=item.email,
            role=item.role,
            expires_at=item.expires_at,
            token=token,
        )

    def revoke_invitation(self, organization_id: int, actor_id: int, invitation_id: int):
        self._membership(organization_id, actor_id, True)
        item = self.repository.invitation(invitation_id)
        if item is None or item.organization_id != organization_id:
            raise OrganizationError("Invitation not found")
        item.revoked_at = datetime.now(UTC)
        self.repository.save(item)
        self._activity(organization_id, actor_id, "INVITATION_REVOKED", "invitation", str(item.id))

    def accept_invitation(self, user_id: int, token: str) -> OrganizationRead:
        item = self.repository.invitation_by_hash(hashlib.sha256(token.encode()).hexdigest())
        now = datetime.now(UTC)
        if item is None or item.revoked_at or item.accepted_at:
            raise OrganizationError("Invitation not found")
        expires_at = item.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            raise OrganizationError("Invitation expired")
        if self.repository.member(item.organization_id, user_id):
            raise OrganizationError("User is already a member")
        organization = self.repository.organization(item.organization_id)
        member_limit = int(organization.limits.get("members", 5))
        if len(self.repository.members(item.organization_id)) >= member_limit:
            raise OrganizationError("Organization member limit reached")
        member = self.repository.save(
            OrganizationMember(
                organization_id=item.organization_id,
                user_id=user_id,
                role=item.role,
                is_default=not self.repository.organizations(user_id),
            )
        )
        item.accepted_at = now
        self.repository.save(item)
        self._activity(
            item.organization_id, user_id, "INVITATION_ACCEPTED", "member", str(member.id)
        )
        return self._read(self.repository.organization(item.organization_id), member)

    def activities(self, organization_id: int, user_id: int, offset: int, limit: int):
        self._membership(organization_id, user_id)
        return [
            ActivityRead(
                id=item.id,
                actor_id=item.actor_id,
                action=item.action,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                metadata=item.metadata_payload,
                created_at=item.created_at,
            )
            for item in self.repository.activities(organization_id, offset, limit)
        ]

    def link_project(self, organization_id: int, user_id: int, project_id: int):
        self._membership(organization_id, user_id, True)
        organization = self.repository.organization(organization_id)
        project_limit = int(organization.limits.get("projects", 10))
        if len(self.repository.projects(organization_id)) >= project_limit:
            raise OrganizationError("Organization project limit reached")
        self.repository.save(
            OrganizationProject(organization_id=organization_id, project_id=project_id)
        )
        self._activity(organization_id, user_id, "PROJECT_LINKED", "project", str(project_id))
        return self.repository.projects(organization_id)

    def projects(self, organization_id: int, user_id: int):
        self._membership(organization_id, user_id)
        return self.repository.projects(organization_id)
