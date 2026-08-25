"""Retire jobs the sources have stopped listing.

Stale jobs are deactivated, never deleted: the statistics page still counts
them, and a job that reappears is recognized rather than re-ingested.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Job

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")
logger = logging.getLogger(__name__)

UNSEEN_DAYS = 14


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        cutoff = datetime.now(UTC) - timedelta(days=UNSEEN_DAYS)
        stale = db.scalars(
            select(Job).where(Job.is_active.is_(True), Job.last_seen_at < cutoff)
        ).all()
        for job in stale:
            job.is_active = False
        db.commit()
        logger.info(
            "cleanup: deactivated %d jobs unseen for %d days (freshness window %dh)",
            len(stale),
            UNSEEN_DAYS,
            settings.max_job_age_hours,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
