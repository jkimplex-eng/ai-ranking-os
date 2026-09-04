import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from alice_learning.automation_adapters import build_alice_automation_service
from alice_learning.integration import learn_from_completed_research
from backend.app.config import get_settings
from backend.app.database import SessionLocal
from backend.app.logging import configure_logging
from competitor_intelligence.service import CompetitorIntelligenceService
from competitor_intelligence.social_monitor import CompetitorSocialMonitorService
from competitor_intelligence.telegram_connector import TelegramConnectionService
from provider_connections.crypto import SecretCipher
from provider_connections.repository import ProviderConnectionRepository
from provider_connections.service import hydrate_provider_credentials
from research.queue import process_next
from scheduler.research_adapter import build_scheduler_engine

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
    last_scheduler_run = 0.0
    loop = asyncio.get_running_loop()
    try:
        while True:
            with SessionLocal() as db:
                job = process_next(db)
                if job is not None:
                    logger.info("Research job processed id=%s state=%s", job.id, job.state)
                    CompetitorIntelligenceService(db).ingest_research(job.research_id)
                    try:
                        learned = learn_from_completed_research(db, job.research_id)
                        if learned:
                            logger.info(
                                "Alice learning observations ingested research_id=%s count=%s",
                                job.research_id,
                                learned,
                            )
                    except Exception:  # noqa: BLE001 - learning cannot fail completed research
                        logger.exception("Alice learning failed research_id=%s", job.research_id)
                now = loop.time()
                if now - last_scheduler_run >= 60:
                    try:
                        executions = build_scheduler_engine(db).run_due()
                        for execution in executions:
                            if execution.research_id is not None:
                                CompetitorIntelligenceService(db).ingest_research(
                                    execution.research_id
                                )
                        if executions:
                            logger.info("Scheduled research processed count=%s", len(executions))
                        social_sources = CompetitorSocialMonitorService(db).run_due()
                        if social_sources:
                            logger.info(
                                "Competitor social sources refreshed count=%s", social_sources
                            )
                        telegram_searches = TelegramConnectionService(db).run_due()
                        if telegram_searches:
                            logger.info(
                                "Telegram brand searches processed count=%s", telegram_searches
                            )
                        alice_runs = build_alice_automation_service(db).run_due()
                        if alice_runs:
                            logger.info(
                                "Alice automated monitoring processed count=%s", len(alice_runs)
                            )
                    except Exception:  # noqa: BLE001 - worker must survive scheduler failures
                        logger.exception("Scheduled research processing failed")
                    last_scheduler_run = now
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
