from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from product.service import ProductNotFoundError
from research_lab.repository import PublicationNotFoundError, PublicationRepository
from research_lab.schemas import (
    ObservationCreate,
    ObservationRead,
    PublicationCreate,
    PublicationRead,
    ResearchDiff,
    ResearchLaboratory,
)
from research_lab.service import ResearchLaboratoryService

router = APIRouter(tags=["research-laboratory"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/research/{research_id}/laboratory", response_model=ResearchLaboratory)
def get_laboratory(research_id: int, db: DbSession) -> ResearchLaboratory:
    try:
        return ResearchLaboratoryService(db).get(research_id)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research/diff", response_model=ResearchDiff)
def diff_research(
    db: DbSession,
    left: int = Query(ge=1),
    right: int = Query(ge=1),
) -> ResearchDiff:
    try:
        return ResearchLaboratoryService(db).diff(left, right)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post(
    "/research-publications",
    response_model=PublicationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_publication(payload: PublicationCreate, db: DbSession) -> PublicationRead:
    return PublicationRepository(db).create(payload)


@router.get("/research-publications", response_model=list[PublicationRead])
def list_publications(entity_id: UUID, db: DbSession) -> list[PublicationRead]:
    return PublicationRepository(db).list_for_entity(entity_id)


@router.post(
    "/research-publications/{publication_id}/observations",
    response_model=ObservationRead,
    status_code=status.HTTP_201_CREATED,
)
def record_observation(
    publication_id: int, payload: ObservationCreate, db: DbSession
) -> ObservationRead:
    try:
        return PublicationRepository(db).record_observation(publication_id, payload)
    except PublicationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
