from sqlalchemy import select
from sqlalchemy.orm import Session

from yandex_webmaster.models import YandexWebmasterConnection, YandexWebmasterOAuthState


class YandexWebmasterRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def connection(self, organization_id: int) -> YandexWebmasterConnection | None:
        return self.db.scalar(
            select(YandexWebmasterConnection).where(
                YandexWebmasterConnection.organization_id == organization_id
            )
        )

    def state(self, state_hash: str) -> YandexWebmasterOAuthState | None:
        return self.db.get(YandexWebmasterOAuthState, state_hash)

    def save(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item) -> None:
        self.db.delete(item)
        self.db.commit()
