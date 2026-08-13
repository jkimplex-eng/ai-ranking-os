from sqlalchemy import select
from sqlalchemy.orm import Session

from organization_workspace.models import OrganizationActivity
from provider_connections.models import ProviderConnection


class ProviderConnectionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, organization_id: int) -> list[ProviderConnection]:
        return list(
            self.db.scalars(
                select(ProviderConnection)
                .where(ProviderConnection.organization_id == organization_id)
                .order_by(ProviderConnection.created_at)
            )
        )

    def connected(self) -> list[ProviderConnection]:
        return list(
            self.db.scalars(
                select(ProviderConnection).where(ProviderConnection.status == "CONNECTED")
            )
        )

    def get(self, connection_id: int) -> ProviderConnection | None:
        return self.db.get(ProviderConnection, connection_id)

    def by_provider(self, organization_id: int, provider: str) -> ProviderConnection | None:
        return self.db.scalar(
            select(ProviderConnection).where(
                ProviderConnection.organization_id == organization_id,
                ProviderConnection.provider == provider,
            )
        )

    def save(self, item: ProviderConnection) -> ProviderConnection:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item: ProviderConnection) -> None:
        self.db.delete(item)
        self.db.commit()

    def audit(
        self, organization_id: int, actor_id: int, action: str, connection_id: int
    ) -> None:
        self.db.add(
            OrganizationActivity(
                organization_id=organization_id,
                actor_id=actor_id,
                action=action,
                entity_type="provider_connection",
                entity_id=str(connection_id),
                metadata_payload={},
            )
        )
        self.db.commit()
