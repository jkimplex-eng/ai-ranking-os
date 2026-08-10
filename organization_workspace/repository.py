from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from organization_workspace.models import (
    Organization,
    OrganizationActivity,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationProject,
)


class OrganizationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def organizations(self, user_id: int):
        return list(
            self.db.execute(
                select(Organization, OrganizationMember)
                .join(OrganizationMember)
                .where(OrganizationMember.user_id == user_id)
                .order_by(Organization.name)
            ).all()
        )

    def organization(self, organization_id: int):
        return self.db.get(Organization, organization_id)

    def member(self, organization_id: int, user_id: int):
        return self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )

    def members(self, organization_id: int):
        return list(
            self.db.scalars(
                select(OrganizationMember)
                .where(OrganizationMember.organization_id == organization_id)
                .order_by(OrganizationMember.joined_at)
            )
        )

    def clear_default(self, user_id: int):
        self.db.execute(
            update(OrganizationMember)
            .where(OrganizationMember.user_id == user_id)
            .values(is_default=False)
        )
        self.db.commit()

    def remove_member(self, member: OrganizationMember):
        self.db.delete(member)
        self.db.commit()

    def invitation(self, invitation_id: int):
        return self.db.get(OrganizationInvitation, invitation_id)

    def invitation_by_hash(self, token_hash: str):
        return self.db.scalar(
            select(OrganizationInvitation).where(OrganizationInvitation.token_hash == token_hash)
        )

    def activities(self, organization_id: int, offset: int, limit: int):
        return list(
            self.db.scalars(
                select(OrganizationActivity)
                .where(OrganizationActivity.organization_id == organization_id)
                .order_by(OrganizationActivity.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )

    def projects(self, organization_id: int):
        return list(
            self.db.scalars(
                select(OrganizationProject.project_id).where(
                    OrganizationProject.organization_id == organization_id
                )
            )
        )

    def unlink_project(self, organization_id: int, project_id: int):
        self.db.execute(
            delete(OrganizationProject).where(
                OrganizationProject.organization_id == organization_id,
                OrganizationProject.project_id == project_id,
            )
        )
        self.db.commit()
