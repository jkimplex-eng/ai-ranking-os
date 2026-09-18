from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from frozen_prompts.models import FrozenPromptInstance, FrozenPromptSet


class FrozenPromptRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, prompt_set_id: UUID) -> FrozenPromptSet | None:
        return self.db.scalar(
            select(FrozenPromptSet)
            .options(selectinload(FrozenPromptSet.instances))
            .where(FrozenPromptSet.id == prompt_set_id)
        )

    def get_instance(self, query_id: UUID) -> FrozenPromptInstance | None:
        return self.db.get(FrozenPromptInstance, query_id)

    def list(self, code: str | None = None) -> list[FrozenPromptSet]:
        statement = select(FrozenPromptSet).options(selectinload(FrozenPromptSet.instances))
        if code:
            statement = statement.where(FrozenPromptSet.code == code)
        return list(
            self.db.scalars(
                statement.order_by(FrozenPromptSet.code, FrozenPromptSet.version.desc())
            )
        )

    def save(self, item: FrozenPromptSet) -> FrozenPromptSet:
        self.db.add(item)
        self.db.commit()
        return self.get(item.id)  # type: ignore[return-value]

    def activate(self, item: FrozenPromptSet) -> FrozenPromptSet:
        self.db.execute(
            update(FrozenPromptSet).where(FrozenPromptSet.code == item.code).values(active=False)
        )
        item.active = True
        return self.save(item)

    def replace_instances(
        self, item: FrozenPromptSet, instances: list[FrozenPromptInstance]
    ) -> FrozenPromptSet:
        item.instances.clear()
        item.instances.extend(instances)
        return self.save(item)
