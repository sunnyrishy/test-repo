"""Scheduled pipeline worker. The interval comes from configuration."""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.database import SessionLocal
from app.services.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def pipeline_job() -> None:
    db = SessionLocal()
    try:
        await run_pipeline(db)
    except Exception:  # noqa: BLE001 - never let one run kill the scheduler
        logger.exception("pipeline run failed")
    finally:
        db.close()


async def main() -> None:
    settings = get_settings()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        pipeline_job, "interval", minutes=settings.job_discovery_interval_minutes
    )
    scheduler.start()
    logger.info(
        "worker started; pipeline interval=%d minutes",
        settings.job_discovery_interval_minutes,
    )
    await pipeline_job()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
