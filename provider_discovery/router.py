from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.app.database import get_db
from provider_discovery.service import ProviderDiscoveryService


class SyncRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    status: str
    discovered: int
    created: int
    updated: int
    error: str | None


router = APIRouter(prefix="/providers", tags=["provider-discovery"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/sync", response_model=SyncRead, status_code=status.HTTP_201_CREATED)
def sync_providers(db: DbSession) -> SyncRead:
    return SyncRead.model_validate(ProviderDiscoveryService(db).sync())
