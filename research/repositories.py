from __future__ import annotations

from contextlib import suppress
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from backend.app.database import Base
from research.models import Research, ResearchTask, Response
from research.schemas import (
    ResearchCreate,
    ResearchTaskCreate,
    ResearchTaskUpdate,
    ResearchUpdate,
    ResponseCreate,
    ResponseUpdate,
)


class EntityNotFoundError(LookupError):
    """Requested research entity does not exist."""


class Repository[ModelT: Base]:
    model: type[ModelT]
    entity_name: str

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, entity_id: int) -> ModelT:
        entity = self.db.get(self.model, entity_id)
        if entity is None:
            raise EntityNotFoundError(f"{self.entity_name} {entity_id} not found")
        return entity

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        query: Select[tuple[ModelT]] | None = None,
    ) -> list[ModelT]:
        statement = select(self.model) if query is None else query
        return list(
            self.db.scalars(
                statement.order_by(self.model.id).offset(offset).limit(limit)
            )
        )

    def delete(self, entity_id: int) -> None:
        entity = self.get(entity_id)
        self.db.delete(entity)
        self.db.commit()

    def _save(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    @staticmethod
    def _changes(payload: Any) -> dict[str, Any]:
        changes = payload.model_dump(exclude_unset=True)
        if "metadata" in changes:
            changes["metadata_payload"] = changes.pop("metadata")
        return changes


class ResearchRepository(Repository[Research]):
    model = Research
    entity_name = "Research"

    def create(self, payload: ResearchCreate) -> Research:
        values = payload.model_dump()
        values["metadata_payload"] = values.pop("metadata")
        return self._save(Research(**values))

    def update(self, research_id: int, payload: ResearchUpdate) -> Research:
        research = self.get(research_id)
        for field, value in self._changes(payload).items():
            setattr(research, field, value)
        return self._save(research)

class ResearchTaskRepository(Repository[ResearchTask]):
    model = ResearchTask
    entity_name = "ResearchTask"

    def create(self, payload: ResearchTaskCreate) -> ResearchTask:
        ResearchRepository(self.db).get(payload.research_id)
        values = payload.model_dump()
        values["metadata_payload"] = values.pop("metadata")
        return self._save(ResearchTask(**values))

    def update(self, task_id: int, payload: ResearchTaskUpdate) -> ResearchTask:
        task = self.get(task_id)
        for field, value in self._changes(payload).items():
            setattr(task, field, value)
        return self._save(task)

    def list_for_research(
        self,
        research_id: int,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ResearchTask]:
        ResearchRepository(self.db).get(research_id)
        return self.list(
            offset=offset,
            limit=limit,
            query=select(ResearchTask).where(ResearchTask.research_id == research_id),
        )


class ResponseRepository(Repository[Response]):
    model = Response
    entity_name = "Response"

    def create(self, payload: ResponseCreate) -> Response:
        ResearchTaskRepository(self.db).get(payload.research_task_id)
        values = payload.model_dump()
        values["raw_response"] = values["raw_response"] or values["raw_payload"]
        values["normalized_response"] = values["normalized_response"] or {
            "content": values["content"],
            "citations": [],
            "finish_reason": "stop",
            "usage": {
                "input_tokens": values["prompt_tokens"],
                "output_tokens": values["completion_tokens"],
                "total_tokens": values["total_tokens"],
                "cost": values["cost"],
                "currency": "USD",
            },
            "metadata": {},
        }
        values["input_tokens"] = values["prompt_tokens"]
        values["output_tokens"] = values["completion_tokens"]
        if values["finished_at"] is None:
            values.pop("finished_at")
        response = self._save(Response(**values))
        from research.extraction import (  # noqa: PLC0415
            ExtractionProcessingError,
            ExtractionService,
        )

        with suppress(ExtractionProcessingError):
            ExtractionService(self.db).extract(response.id)
        self.db.refresh(response)
        return response

    def update(self, response_id: int, payload: ResponseUpdate) -> Response:
        response = self.get(response_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(response, field, value)
        response.total_tokens = response.prompt_tokens + response.completion_tokens
        response.input_tokens = response.prompt_tokens
        response.output_tokens = response.completion_tokens
        return self._save(response)

    def list_for_task(
        self,
        research_task_id: int,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Response]:
        ResearchTaskRepository(self.db).get(research_task_id)
        return self.list(
            offset=offset,
            limit=limit,
            query=select(Response).where(
                Response.research_task_id == research_task_id
            ),
        )
