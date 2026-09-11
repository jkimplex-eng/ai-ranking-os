from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
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
        raise ValueError("Сначала создайте организацию")
    selected = next((org.id for org, member in memberships if member.is_default), None)
    return selected or memberships[0][0].id


ConnectionService = Annotated[ProviderConnectionService, Depends(service)]
