from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database import Base
from app.models import Job, JobScore, Notification
from app.services import notification as notifications


@pytest.fixture
def settings():
    return Settings(
        database_url="sqlite://",
        smtp_host="smtp.example.com",
        notification_email="me@example.com",
        notification_min_score=90,
    )


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path/'n.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


def add_scored_job(db, title, score):
    job = Job(
        external_id=title,
        source="greenhouse",
        company="ABC Corp",
        title=title,
        location="New York, NY",
        application_url="https://example.com/apply",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        is_active=True,
    )
    db.add(job)
    db.flush()
    db.add(JobScore(job_id=job.id, overall_score=score, classification="STRONG"))
    db.commit()
    return job


def test_only_high_scoring_jobs_are_notified(db):
    add_scored_job(db, "Software Engineer I", 96)
    add_scored_job(db, "Backend Engineer", 72)
    pending = notifications.pending_jobs(db, "email", 90)
    assert [job.title for job, _ in pending] == ["Software Engineer I"]


def test_digest_is_one_message_covering_every_job(db):
    add_scored_job(db, "Software Engineer I", 96)
    add_scored_job(db, "Backend Engineer", 93)
    subject, body = notifications.render_digest(notifications.pending_jobs(db, "email", 90))
    assert "2 new high-match software jobs" in subject
    assert "Software Engineer I" in body and "Backend Engineer" in body
    assert "96/100" in body


def test_a_job_is_not_notified_about_twice(db, settings, monkeypatch):
    add_scored_job(db, "Software Engineer I", 96)
    sent = []
    monkeypatch.setattr(
        notifications, "configured_channels",
        lambda s: {"email": lambda s, subject, body: sent.append(subject)},
    )

    assert notifications.send_digests(db, settings)["jobs"] == 1
    assert db.query(Notification).count() == 1
    # Second run has nothing new to say.
    assert notifications.send_digests(db, settings)["jobs"] == 0
    assert len(sent) == 1


def test_a_failing_channel_leaves_its_jobs_for_the_next_run(db, settings, monkeypatch):
    add_scored_job(db, "Software Engineer I", 96)

    def explode(*_args):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(
        notifications, "configured_channels", lambda s: {"email": explode}
    )
    stats = notifications.send_digests(db, settings)
    assert stats["sent"] == 0 and stats["errors"]
    assert db.query(Notification).count() == 0


def test_channels_are_configured_by_environment():
    assert notifications.configured_channels(Settings(database_url="sqlite://")) == {}
    configured = notifications.configured_channels(
        Settings(
            database_url="sqlite://",
            smtp_host="smtp.example.com",
            notification_email="me@example.com",
            discord_webhook_url="https://discord.example/hook",
        )
    )
    assert sorted(configured) == ["discord", "email"]
