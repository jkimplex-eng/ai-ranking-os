from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from provider_registry.repository import ProviderNotFoundError
from provider_registry.schemas import CapabilityMatrix, ProviderRead
from provider_registry.service import ProviderRegistryService

router = APIRouter(prefix="/providers", tags=["provider-registry"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ProviderRead])
def list_providers(db: DbSession) -> list[ProviderRead]:
    return ProviderRegistryService.from_session(db).list()


@router.get("/capabilities", response_model=CapabilityMatrix)
def provider_capabilities(db: DbSession) -> CapabilityMatrix:
    return ProviderRegistryService.from_session(db).capabilities()


@router.get("/{provider_id}", response_model=ProviderRead)
def get_provider(provider_id: str, db: DbSession) -> ProviderRead:
    try:
        return ProviderRegistryService.from_session(db).get(provider_id)
    except ProviderNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
