import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from backend.app.config import get_settings

settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Keep a worker process alive and verify its Redis connection."""

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("AI Ranking OS worker starting")
    try:
        while True:
            try:
                await client.ping()
                logger.info("Worker heartbeat: Redis is available")
            except RedisError:
                logger.exception("Worker heartbeat failed")
            await asyncio.sleep(30)
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(run_worker())

