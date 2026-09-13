from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from frozen_prompts.repository import FrozenPromptRepository
from frozen_prompts.schemas import FanOutRequest, FanOutResult, PromptSetCreate, PromptSetRead
from frozen_prompts.service import FrozenPromptService, PromptSetNotFoundError

router = APIRouter(prefix="/geo/prompt-sets", tags=["geo-prompt-sets"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=PromptSetRead, status_code=status.HTTP_201_CREATED)
def create_prompt_set(payload: PromptSetCreate, db: DbSession) -> PromptSetRead:
    try:
        return FrozenPromptService(FrozenPromptRepository(db)).create(payload)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[PromptSetRead])
def list_prompt_sets(db: DbSession, code: str | None = None) -> list[PromptSetRead]:
    return FrozenPromptRepository(db).list(code)


@router.get("/{prompt_set_id}", response_model=PromptSetRead)
def get_prompt_set(prompt_set_id: UUID, db: DbSession) -> PromptSetRead:
    item = FrozenPromptRepository(db).get(prompt_set_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Prompt set {prompt_set_id} not found")
    return item


@router.post("/{prompt_set_id}/activate", response_model=PromptSetRead)
def activate_prompt_set(prompt_set_id: UUID, db: DbSession) -> PromptSetRead:
    try:
        return FrozenPromptService(FrozenPromptRepository(db)).activate(prompt_set_id)
    except PromptSetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{prompt_set_id}/fan-out", response_model=FanOutResult)
def fan_out(prompt_set_id: UUID, payload: FanOutRequest, db: DbSession) -> FanOutResult:
    try:
        item = FrozenPromptService(FrozenPromptRepository(db)).fan_out(prompt_set_id, payload)
        return FanOutResult(
            prompt_set_id=item.id, fingerprint=item.fingerprint, instances=item.instances
        )
    except PromptSetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
