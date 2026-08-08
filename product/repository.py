from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from product.models import PromptDefinition, PromptStatus, ResearchTemplateDefinition
from product.schemas import PromptCreate, PromptUpdate


class ProductNotFoundError(LookupError):
    pass


class ProductConflictError(ValueError):
    pass


class PromptRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: PromptCreate) -> PromptDefinition:
        item = PromptDefinition(**payload.model_dump())
        self.db.add(item)
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise ProductConflictError("Prompt code/version already exists") from error
        self.db.refresh(item)
        return item

    def list(
        self, *, category: str | None = None, language: str | None = None
    ) -> list[PromptDefinition]:
        statement = select(PromptDefinition)
        if category:
            statement = statement.where(PromptDefinition.category == category)
        if language:
            statement = statement.where(PromptDefinition.language == language)
        return list(
            self.db.scalars(
                statement.order_by(PromptDefinition.code, PromptDefinition.version.desc())
            )
        )

    def get(self, prompt_id: int) -> PromptDefinition:
        item = self.db.get(PromptDefinition, prompt_id)
        if item is None:
            raise ProductNotFoundError(f"Prompt {prompt_id} not found")
        return item

    def active(self, code: str, language: str | None = None) -> PromptDefinition:
        base = select(PromptDefinition).where(
            PromptDefinition.code == code, PromptDefinition.active.is_(True)
        )
        statement = base
        if language:
            statement = base.where(PromptDefinition.language == language)
        item = self.db.scalar(statement.order_by(PromptDefinition.version.desc()))
        if item is None and language and language != "en":
            item = self.db.scalar(
                base.where(PromptDefinition.language == "en").order_by(
                    PromptDefinition.version.desc()
                )
            )
        if item is None:
            raise ProductNotFoundError(f"Active prompt {code} not found")
        return item

    def update(self, prompt_id: int, payload: PromptUpdate) -> PromptDefinition:
        item = self.get(prompt_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def clone(self, prompt_id: int) -> PromptDefinition:
        source = self.get(prompt_id)
        version = (
            self.db.scalar(
                select(func.max(PromptDefinition.version)).where(
                    PromptDefinition.code == source.code
                )
            )
            or 0
        ) + 1
        return self.create(
            PromptCreate(
                code=source.code,
                version=version,
                title=source.title,
                description=source.description,
                category=source.category,
                language=source.language,
                variables=source.variables,
                template=source.template,
                expected_output=source.expected_output,
                tags=source.tags,
            )
        )

    def activate(self, prompt_id: int) -> PromptDefinition:
        item = self.get(prompt_id)
        self.db.execute(
            update(PromptDefinition)
            .where(
                PromptDefinition.code == item.code,
                PromptDefinition.language == item.language,
            )
            .values(active=False)
        )
        item.active = True
        item.status = PromptStatus.ACTIVE
        self.db.commit()
        self.db.refresh(item)
        return item

    def deprecate(self, prompt_id: int) -> PromptDefinition:
        item = self.get(prompt_id)
        item.active = False
        item.status = PromptStatus.DEPRECATED
        self.db.commit()
        self.db.refresh(item)
        return item


class ResearchTemplateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[ResearchTemplateDefinition]:
        return list(
            self.db.scalars(
                select(ResearchTemplateDefinition)
                .where(ResearchTemplateDefinition.active.is_(True))
                .order_by(ResearchTemplateDefinition.title)
            )
        )

    def get(self, code: str) -> ResearchTemplateDefinition:
        item = self.db.scalar(
            select(ResearchTemplateDefinition)
            .where(
                ResearchTemplateDefinition.code == code,
                ResearchTemplateDefinition.active.is_(True),
            )
            .order_by(ResearchTemplateDefinition.version.desc())
        )
        if item is None:
            raise ProductNotFoundError(f"Research template {code} not found")
        return item
