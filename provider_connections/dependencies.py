from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from authentication.models import AuthUser
from backend.app.config import get_settings
from backend.app.database import get_db
from organization_workspace.models import Organization, OrganizationMember
from organization_workspace.repository import OrganizationRepository
from provider_connections.crypto import SecretCipher
from provider_connections.repository import ProviderConnectionRepository
from provider_connections.service import ProviderConnectionService


def service(db: Annotated[Session, Depends(get_db)]) -> ProviderConnectionService:
    settings = get_settings()
    encryption_secret = settings.provider_secret_key or settings.auth_jwt_secret
    return ProviderConnectionService(
        ProviderConnectionRepository(db), SecretCipher(encryption_secret)
    )


def default_organization(db: Session, user_id: int) -> int:
    memberships = OrganizationRepository(db).organizations(user_id)
    if not memberships:
        # Serialize first-use provisioning: the GEO page requests several APIs
        # concurrently. Never attach an account to somebody else's organization.
        user = db.scalar(select(AuthUser).where(AuthUser.id == user_id).with_for_update())
        if user is None or not user.is_active:
            raise HTTPException(401, "Authentication required")
        memberships = OrganizationRepository(db).organizations(user_id)
        if not memberships:
            from uuid import uuid4

            organization = Organization(
                name=f"Рабочее пространство {user.display_name}"[:200],
                slug=f"personal-{user_id}-{uuid4().hex[:12]}",
            )
            db.add(organization)
            db.flush()
            db.add(
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=user_id,
                    role="OWNER",
                    is_default=True,
                )
            )
            db.commit()
            return organization.id
    selected = next((org.id for org, member in memberships if member.is_default), None)
    return selected or memberships[0][0].id


ConnectionService = Annotated[ProviderConnectionService, Depends(service)]
