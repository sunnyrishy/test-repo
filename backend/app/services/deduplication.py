"""Deduplication: one canonical job per real vacancy.

Matching runs in priority order - exact source + external id (in the ingestion
path), then the company/title/location fingerprint below. Semantic similarity
matching is deliberately not implemented: it needs embeddings, and the cheaper
keys resolve the duplicates we actually see.
"""
from __future__ import annotations

import hashlib

from typing import TYPE_CHECKING

from app.schemas.job import NormalizedJob
from app.services import normalization as norm

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Job


def fingerprint(job: NormalizedJob) -> str:
    """company + title + location, normalized, hashed."""
    key = "|".join(
        (
            norm.normalize_company(job.company),
            norm.normalize_title(job.title),
            norm.normalize_location(job.location),
        )
    )
    return hashlib.sha256(key.encode()).hexdigest()[:32]


# --- canonical merging (Phase 4) ---------------------------------------------

# Sources that are the employer's own ATS, in order of preference. A canonical
# job prefers the employer's application URL over any aggregator's.
CANONICAL_SOURCE_PRIORITY = ("greenhouse", "lever", "ashby", "company", "wellfound")


def source_rank(source: str) -> int:
    try:
        return CANONICAL_SOURCE_PRIORITY.index(source)
    except ValueError:
        return len(CANONICAL_SOURCE_PRIORITY)


def pick_canonical(jobs: "list[Job]") -> "Job":
    """The employer-side posting wins; ties break on the earliest sighting."""
    return min(
        jobs,
        key=lambda job: (
            source_rank(job.source),
            job.application_url is None,
            job.first_seen_at,
        ),
    )


def merge_duplicates(db: "Session") -> dict:
    """Group active jobs by fingerprint and fold each group into one canonical
    job, recording every source so the UI can link all of them.

    Duplicates are not deleted - they are marked inactive and pointed at the
    canonical job, so a later run recognizes them instead of re-ingesting.
    """
    from sqlalchemy import select

    from app.models import Job

    groups: dict[str, list[Job]] = {}
    for job in db.scalars(select(Job).where(Job.is_active.is_(True))).all():
        if job.fingerprint:
            groups.setdefault(job.fingerprint, []).append(job)

    stats = {"groups": 0, "merged": 0}
    for jobs in groups.values():
        if len(jobs) < 2:
            continue
        canonical = pick_canonical(jobs)
        known = {(source.source, source.source_job_id) for source in canonical.sources}
        stats["groups"] += 1

        for duplicate in jobs:
            if duplicate.id == canonical.id:
                continue
            # Reassign the duplicate's provenance rows instead of copying them:
            # (source, source_job_id) is globally unique, and the history of
            # when each source first saw the job is worth keeping.
            for source in list(duplicate.sources):
                key = (source.source, source.source_job_id)
                if key in known:
                    continue
                known.add(key)
                duplicate.sources.remove(source)
                canonical.sources.append(source)

            # Keep the best information we have across the duplicates, without
            # inventing anything neither posting stated.
            if canonical.posted_at is None:
                canonical.posted_at = duplicate.posted_at
            if canonical.description is None:
                canonical.description = duplicate.description
            if canonical.salary_max is None:
                canonical.salary_min = duplicate.salary_min
                canonical.salary_max = duplicate.salary_max
                canonical.currency = duplicate.currency

            duplicate.canonical_job_id = canonical.id
            duplicate.is_active = False
            stats["merged"] += 1

    db.commit()
    return stats
