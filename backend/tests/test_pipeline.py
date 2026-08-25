"""End-to-end: ingest -> merge -> verify -> score -> API, on a real database."""
import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database import Base, get_db
from app.main import app
from app.models import CandidateProfile, Job, JobScore, JobVerification
from app.schemas.job import EmploymentType, NormalizedJob
from app.services.discovery import RunStats, ingest
from app.services.deduplication import merge_duplicates
from app.services.scoring import run_scoring
from app.services.verification import run_verification


@pytest.fixture
def settings(tmp_path):
    from app.config import REPO_ROOT

    return Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path/'pipeline.db'}",
        ai_provider="mock",
        min_match_score=0,
        candidate_profile_path=REPO_ROOT / "config" / "candidate_profile.yaml",
        prompts_path=REPO_ROOT / "prompts",
    )


@pytest.fixture
def db(settings, monkeypatch):
    import app.config

    monkeypatch.setattr(app.config, "get_settings", lambda: settings)
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


def job(**overrides) -> NormalizedJob:
    base = dict(
        external_id="1",
        source="greenhouse",
        company="ABC Corp",
        title="Software Engineer I",
        location="New York, NY",
        country="US",
        employment_type=EmploymentType.FULL_TIME,
        description="Entry level. 0-1 years of experience. Sponsorship available.",
        application_url="https://example.com/apply",
        posted_at=datetime.now(UTC) - timedelta(hours=3),
    )
    base.update(overrides)
    return NormalizedJob(**base)


def test_full_pipeline(db, settings):
    stats = RunStats()
    ingest(
        db,
        [
            job(),
            job(source="linkedin", external_id="l1"),          # same vacancy
            job(external_id="2", title="Senior Software Engineer"),  # hard rejected
            job(external_id="3", title="Business Analyst"),          # role excluded
        ],
        stats,
        settings,
    )
    assert stats.discovered == 4
    assert stats.passed_filters == 1
    assert stats.hard_filter_failures == 2
    # The LinkedIn sighting of the same vacancy is folded into one job, but its
    # source link is kept rather than discarded.
    assert stats.duplicates == 1
    assert stats.stored == 3

    merge_duplicates(db)

    verification_stats = asyncio.run(run_verification(db, settings))
    assert verification_stats["verified"] == 1
    # The mock provider determines nothing, so the job lands in REVIEW, not PASS.
    assert verification_stats["review"] == 1

    verification = db.query(JobVerification).one()
    assert verification.model == "mock"
    assert verification.sponsorship_status == "AVAILABLE"

    # REVIEW is not PASS, so nothing is scored and nothing reaches the dashboard.
    assert run_scoring(db, settings)["scored"] == 0

    # Promote it as a real model would, then score.
    for field in (
        "role_match", "entry_level", "experience_match", "degree_match",
        "graduation_match", "location_match", "employment_match",
    ):
        setattr(verification, field, True)
    verification.citizenship_required = False
    verification.security_clearance_required = False
    verification.decision = "PASS"
    verification.experience_required = 0
    verification.matched_skills = ["Python", "SQL"]
    db.commit()

    assert run_scoring(db, settings)["scored"] == 1
    score = db.query(JobScore).one()
    assert 70 <= score.overall_score <= 100

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[
        __import__("app.config", fromlist=["get_settings"]).get_settings
    ] = lambda: settings
    try:
        client = TestClient(app)
        listing = client.get("/api/jobs").json()
        assert listing["total"] == 1
        item = listing["items"][0]
        assert item["title"] == "Software Engineer I"
        assert item["score"]["overall_score"] == score.overall_score
        assert item["verification"]["decision"] == "PASS"
        # Both sources are linked from the one canonical job.
        assert {s["source"] for s in item["sources"]} == {"greenhouse", "linkedin"}

        assert len(client.get("/api/jobs/top").json()) == 1
        assert len(client.get("/api/jobs/recent").json()) == 1

        summary = client.get("/api/jobs/stats").json()
        assert summary["verified_pass"] == 1
        assert summary["by_rejection_reason"] == {
            "SENIORITY_TOO_HIGH": 1,
            "ROLE_EXCLUDED": 1,
        }

        assert client.get(f"/api/jobs/{item['id']}").json()["title"] == item["title"]
    finally:
        app.dependency_overrides.clear()


def test_profile_round_trips_through_the_api(db, settings):
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        current = client.get("/api/profile").json()["profile"]
        assert current["graduation_year"] == 2026

        current["graduation_year"] = 2027
        assert client.put("/api/profile", json=current).status_code == 200
        assert client.get("/api/profile").json()["profile"]["graduation_year"] == 2027
        assert db.query(CandidateProfile).count() == 1
    finally:
        app.dependency_overrides.clear()
