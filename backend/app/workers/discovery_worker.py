"""Scheduled discovery worker. Interval comes from configuration, never hard-coded."""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.database import SessionLocal
from app.services.discovery import run_discovery

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def discovery_job() -> None:
    db = SessionLocal()
    try:
        await run_discovery(db)
    except Exception:  # noqa: BLE001 - never let one run kill the scheduler
        logger.exception("discovery run failed")
    finally:
        db.close()


async def main() -> None:
    settings = get_settings()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        discovery_job,
        "interval",
        minutes=settings.job_discovery_interval_minutes,
        next_run_time=None,
    )
    scheduler.start()
    logger.info(
        "discovery worker started; interval=%d minutes",
        settings.job_discovery_interval_minutes,
    )
    await discovery_job()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
