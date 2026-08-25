"""Canonical merging, against a real database."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import DiscoveryRun, Job, JobSource  # noqa: F401
from app.services.deduplication import fingerprint, merge_duplicates, pick_canonical
from app.schemas.job import NormalizedJob


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path/'test.db'}")
    for table in (Job.__table__, JobSource.__table__):
        table.create(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


def add_job(db, source, external_id, *, url=None, seen_hours_ago=0, **overrides):
    now = datetime.now(UTC)
    normalized = NormalizedJob(
        external_id=external_id,
        source=source,
        company=overrides.pop("company", "Example Inc."),
        title=overrides.pop("title", "Software Engineer"),
        location=overrides.pop("location", "New York, NY"),
    )
    job = Job(
        external_id=external_id,
        source=source,
        company=normalized.company,
        title=normalized.title,
        location=normalized.location,
        country="US",
        application_url=url,
        fingerprint=fingerprint(normalized),
        first_seen_at=now - timedelta(hours=seen_hours_ago),
        last_seen_at=now,
        is_active=True,
        filter_status="PASS",
        **overrides,
    )
    job.sources.append(
        JobSource(source=source, source_job_id=external_id, application_url=url)
    )
    db.add(job)
    db.commit()
    return job


def test_duplicates_across_sources_merge_into_one(db):
    add_job(db, "linkedin", "l1", url="https://linkedin.com/jobs/1")
    add_job(db, "greenhouse", "g1", url="https://boards.greenhouse.io/x/1")

    stats = merge_duplicates(db)
    assert stats == {"groups": 1, "merged": 1}

    active = db.query(Job).filter(Job.is_active.is_(True)).all()
    assert len(active) == 1
    # The employer's own ATS wins over the aggregator.
    assert active[0].source == "greenhouse"
    assert {source.source for source in active[0].sources} == {"greenhouse", "linkedin"}


def test_merged_duplicate_points_at_the_canonical_job(db):
    add_job(db, "linkedin", "l1")
    add_job(db, "lever", "v1")
    merge_duplicates(db)

    canonical = db.query(Job).filter(Job.is_active.is_(True)).one()
    duplicate = db.query(Job).filter(Job.is_active.is_(False)).one()
    assert duplicate.canonical_job_id == canonical.id


def test_distinct_jobs_are_left_alone(db):
    add_job(db, "greenhouse", "g1", title="Software Engineer")
    add_job(db, "greenhouse", "g2", title="Data Engineer")
    assert merge_duplicates(db) == {"groups": 0, "merged": 0}
    assert db.query(Job).filter(Job.is_active.is_(True)).count() == 2


def test_canonical_inherits_facts_the_winner_lacked(db):
    add_job(db, "greenhouse", "g1")
    posted = datetime.now(UTC) - timedelta(hours=5)
    add_job(db, "linkedin", "l1", posted_at=posted, description="Full description here.")

    merge_duplicates(db)
    canonical = db.query(Job).filter(Job.is_active.is_(True)).one()
    assert canonical.source == "greenhouse"
    assert canonical.description == "Full description here."
    assert canonical.posted_at is not None


def test_canonical_prefers_an_ats_with_an_application_url(db):
    aggregator = add_job(db, "indeed", "i1", url="https://indeed.com/1")
    employer = add_job(db, "ashby", "a1", url="https://jobs.ashbyhq.com/x/1")
    assert pick_canonical([aggregator, employer]).source == "ashby"


def test_merging_twice_changes_nothing(db):
    add_job(db, "linkedin", "l1")
    add_job(db, "greenhouse", "g1")
    merge_duplicates(db)
    assert merge_duplicates(db) == {"groups": 0, "merged": 0}
