import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from backend.app.config import get_settings
from backend.app.database import SessionLocal
from backend.app.logging import configure_logging
from provider_connections.crypto import SecretCipher
from provider_connections.repository import ProviderConnectionRepository
from provider_connections.service import hydrate_provider_credentials
from research.queue import process_next

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Keep a worker process alive and verify its Redis connection."""

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("AI Ranking OS worker starting")
    with SessionLocal() as db:
        restored = hydrate_provider_credentials(
            ProviderConnectionRepository(db),
            SecretCipher(settings.provider_secret_key or settings.auth_jwt_secret),
        )
        logger.info("Restored %s provider connection(s)", restored)
    try:
        while True:
            with SessionLocal() as db:
                job = process_next(db)
                if job is not None:
                    logger.info("Research job processed id=%s state=%s", job.id, job.state)
            try:
                await client.ping()
                logger.info("Worker heartbeat: Redis is available")
            except RedisError:
                logger.exception("Worker heartbeat failed")
            await asyncio.sleep(1 if job is not None else 5)
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(run_worker())

