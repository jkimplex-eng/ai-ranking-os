from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apikeys.repository import ApiKeyRepository
from apikeys.schemas import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRead,
    ApiKeyValidation,
    ApiKeyValidationResult,
)
from apikeys.service import ApiKeyError, ApiKeyNotFound, ApiKeyService
from backend.app.database import get_db

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def get_api_key_service(db: Annotated[Session, Depends(get_db)]):
    return ApiKeyService(ApiKeyRepository(db))


Service = Annotated[ApiKeyService, Depends(get_api_key_service)]


def guarded(call):
    try:
        return call()
    except ApiKeyNotFound as e:
        raise HTTPException(404, str(e)) from e
    except ApiKeyError as e:
        raise HTTPException(409, str(e)) from e


@router.post("", response_model=ApiKeyCreated, status_code=201)
def create(payload: ApiKeyCreate, service: Service):
    return guarded(lambda: service.create(payload))


@router.get("", response_model=list[ApiKeyRead])
def list_keys(service: Service, owner_id: int | None = None):
    return service.list(owner_id)


@router.get("/{key_id:int}", response_model=ApiKeyRead)
def get(key_id: int, service: Service):
    return guarded(lambda: service.get(key_id))


@router.post("/{key_id:int}/revoke", response_model=ApiKeyRead)
def revoke(key_id: int, service: Service):
    return guarded(lambda: service.revoke(key_id))


@router.post("/{key_id:int}/rotate", response_model=ApiKeyCreated)
def rotate(key_id: int, service: Service):
    return guarded(lambda: service.rotate(key_id))


@router.post("/validate", response_model=ApiKeyValidationResult)
def validate(payload: ApiKeyValidation, service: Service):
    try:
        p = service.validate(payload.credential, payload.required_scope)
        return ApiKeyValidationResult(
            valid=True,
            key_id=p.key_id,
            owner_id=p.owner_id,
            scopes=list(p.scopes),
            rate_plan=p.rate_plan,
        )
    except ApiKeyError:
        return ApiKeyValidationResult(valid=False)
