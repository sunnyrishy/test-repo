"""The discovery pipeline: fetch -> normalize -> dedupe -> filter -> store.

A failing source is recorded and skipped; it never aborts the run.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import DiscoveryRun, Job, JobSource
from app.schemas.job import FilterStatus, NormalizedJob
from app.services import deduplication, filtering
from app.services.profile import get_profile
from app.sources.base import JobSourceConnector
from app.sources.registry import build_connectors

logger = logging.getLogger(__name__)


@dataclass
class RunStats:
    discovered: int = 0
    duplicates: int = 0
    stored: int = 0
    hard_filter_failures: int = 0
    passed_filters: int = 0
    per_source: dict[str, dict] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


async def fetch_all(connectors: list[JobSourceConnector], stats: RunStats) -> list[NormalizedJob]:
    """Fetch every source concurrently, tolerating individual failures."""
    results = await asyncio.gather(
        *(connector.fetch() for connector in connectors), return_exceptions=True
    )
    jobs: list[NormalizedJob] = []
    for connector, result in zip(connectors, results, strict=True):
        if isinstance(result, BaseException):
            logger.error("source %s FAILED: %s", connector.name, result)
            stats.per_source[connector.name] = {"error": str(result)}
            stats.errors.append(f"{connector.name}: {result}")
            continue
        logger.info("source %s found %d jobs", connector.name, len(result))
        stats.per_source[connector.name] = {"found": len(result)}
        jobs.extend(result)
    return jobs


def ingest(db: Session, jobs: list[NormalizedJob], stats: RunStats, settings: Settings) -> None:
    """Persist normalized jobs and record their deterministic filter outcome."""
    profile = get_profile(db)
    now = datetime.now(UTC)
    seen_fingerprints: set[str] = set()

    for job in jobs:
        stats.discovered += 1
        existing = db.scalar(
            select(Job).where(Job.source == job.source, Job.external_id == job.external_id)
        )
        if existing is not None:
            existing.last_seen_at = now
            existing.is_active = True
            stats.duplicates += 1
            continue

        digest = deduplication.fingerprint(job)
        if digest in seen_fingerprints:
            stats.duplicates += 1
            continue
        seen_fingerprints.add(digest)

        result = filtering.hard_filter(job, profile, settings.max_job_age_hours)
        if result.passed:
            stats.passed_filters += 1
        else:
            stats.hard_filter_failures += 1
            stats.per_source.setdefault(job.source, {}).setdefault("rejections", {})
            rejections = stats.per_source[job.source]["rejections"]
            rejections[result.reason] = rejections.get(result.reason, 0) + 1

        row = Job(
            external_id=job.external_id,
            source=job.source,
            company=job.company,
            title=job.title,
            location=job.location,
            country=job.country,
            workplace_type=job.workplace_type.value,
            employment_type=job.employment_type.value,
            description=job.description,
            application_url=job.application_url,
            source_url=job.source_url,
            posted_at=job.posted_at,
            source_updated_at=job.source_updated_at,
            first_seen_at=now,
            last_seen_at=now,
            freshness_status=filtering.freshness_status(
                job.posted_at, settings.max_job_age_hours
            ).value,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            currency=job.currency,
            fingerprint=digest,
            filter_status=result.status.value,
            filter_rejection_reason=result.reason,
        )
        row.sources.append(
            JobSource(
                source=job.source,
                source_job_id=job.external_id,
                source_url=job.source_url,
                application_url=job.application_url,
                first_seen_at=now,
                last_seen_at=now,
            )
        )
        db.add(row)
        stats.stored += 1

    db.commit()


async def run_discovery(db: Session, settings: Settings | None = None) -> RunStats:
    settings = settings or get_settings()
    stats = RunStats()
    run = DiscoveryRun()
    db.add(run)
    db.commit()

    logger.info("discovery started (run %d)", run.id)
    connectors = build_connectors(settings)
    if not connectors:
        logger.warning("no source connectors configured; set GREENHOUSE_BOARDS/LEVER_BOARDS")

    try:
        jobs = await fetch_all(connectors, stats)
        ingest(db, jobs, stats, settings)
    finally:
        run.finished_at = datetime.now(UTC)
        run.discovered = stats.discovered
        run.duplicates = stats.duplicates
        run.stored = stats.stored
        run.hard_filter_failures = stats.hard_filter_failures
        run.passed_filters = stats.passed_filters
        run.per_source = json.dumps(stats.per_source)
        run.errors = json.dumps(stats.errors) if stats.errors else None
        db.commit()

    logger.info(
        "discovery finished: discovered=%d duplicates=%d stored=%d "
        "hard_filter_failures=%d passed=%d errors=%d",
        stats.discovered,
        stats.duplicates,
        stats.stored,
        stats.hard_filter_failures,
        stats.passed_filters,
        len(stats.errors),
    )
    return stats
