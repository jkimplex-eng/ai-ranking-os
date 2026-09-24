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
            self._scope(select(FrozenPromptSet))
            .options(selectinload(FrozenPromptSet.instances))
            .where(FrozenPromptSet.id == prompt_set_id)
        )

    def get_instance(self, query_id: UUID) -> FrozenPromptInstance | None:
        return self.db.scalar(
            self._scope(
                select(FrozenPromptInstance).join(FrozenPromptSet)
            ).where(FrozenPromptInstance.id == query_id)
        )

    def list(self, code: str | None = None) -> list[FrozenPromptSet]:
        statement = self._scope(select(FrozenPromptSet)).options(
            selectinload(FrozenPromptSet.instances)
        )
        if code:
            statement = statement.where(FrozenPromptSet.code == code)
        return list(
            self.db.scalars(
                statement.order_by(FrozenPromptSet.code, FrozenPromptSet.version.desc())
            )
        )

    def save(self, item: FrozenPromptSet) -> FrozenPromptSet:
        if "geo_organization_id" in self.db.info:
            organization_id = self.db.info["geo_organization_id"]
            if item.organization_id is None:
                item.organization_id = organization_id
            elif item.organization_id != organization_id:
                raise PermissionError("Prompt set belongs to another organization")
        self.db.add(item)
        self.db.commit()
        return self.get(item.id)  # type: ignore[return-value]

    def activate(self, item: FrozenPromptSet) -> FrozenPromptSet:
        self.db.execute(
            update(FrozenPromptSet).where(
                FrozenPromptSet.code == item.code,
                FrozenPromptSet.organization_id == item.organization_id,
            ).values(active=False)
        )
        item.active = True
        return self.save(item)

    def replace_instances(
        self, item: FrozenPromptSet, instances: list[FrozenPromptInstance]
    ) -> FrozenPromptSet:
        item.instances.clear()
        item.instances.extend(instances)
        return self.save(item)

    def _scope(self, statement):
        if "geo_organization_id" in self.db.info:
            return statement.where(
                FrozenPromptSet.organization_id == self.db.info["geo_organization_id"]
            )
        return statement
