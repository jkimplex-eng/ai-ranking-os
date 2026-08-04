from fastapi import APIRouter, Depends, HTTPException
from redis import Redis

from backend.app.config import get_settings
from cache.backend import MemoryCacheBackend
from cache.redis_backend import RedisCacheBackend
from cache.resilient import ResilientCacheBackend
from cache.schemas import CacheInvalidate, CacheWarmRequest
from cache.service import CacheService

router = APIRouter(prefix="/cache", tags=["cache"])
_settings = get_settings()
_backend = ResilientCacheBackend(
    RedisCacheBackend(
        Redis.from_url(
            _settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.5,
            health_check_interval=30,
        )
    ),
    MemoryCacheBackend(),
)


def get_cache_service():
    return CacheService(_backend)


Service = Depends(get_cache_service)


@router.get("/stats")
def stats(service: CacheService = Service):
    return service.backend.stats()


@router.post("/invalidate")
def invalidate(payload: CacheInvalidate, service: CacheService = Service):
    if payload.key:
        return {"invalidated": int(service.backend.delete(payload.key))}
    if payload.tag:
        return {"invalidated": service.backend.invalidate_tag(payload.tag)}
    raise HTTPException(422, "key or tag is required")


@router.post("/warm")
def warm(payload: CacheWarmRequest, service: CacheService = Service):
    return {"warmed": service.warm([x.model_dump() for x in payload.entries])}
