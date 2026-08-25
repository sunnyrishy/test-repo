"""Connector normalization, exercised against recorded payload shapes."""
from datetime import UTC, datetime

from app.schemas.job import EmploymentType, WorkplaceType
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource

GREENHOUSE_PAYLOAD = {
    "id": 4567,
    "title": "Software Engineer I",
    "absolute_url": "https://boards.greenhouse.io/example/jobs/4567",
    "location": {"name": "New York, NY"},
    "content": "&lt;p&gt;Full-time role. 0-1 years of experience.&lt;/p&gt;",
    "first_published": "2026-08-25T10:30:00Z",
    "updated_at": "2026-08-25T12:00:00Z",
    "metadata": [{"name": "Employment Type", "value": "Full-time"}],
}

LEVER_PAYLOAD = {
    "id": "abc-123",
    "text": "Backend Engineer",
    "hostedUrl": "https://jobs.lever.co/example/abc-123",
    "applyUrl": "https://jobs.lever.co/example/abc-123/apply",
    "categories": {"location": "Remote - US", "commitment": "Full-time"},
    "descriptionPlain": "Backend role for early career engineers.",
    "createdAt": 1_756_119_000_000,
    "workplaceType": "remote",
}


def test_greenhouse_normalization():
    job = GreenhouseSource(["example"])._normalize(GREENHOUSE_PAYLOAD, "example")
    assert job.external_id == "4567"
    assert job.company == "example"
    assert job.country == "US"
    assert job.employment_type is EmploymentType.FULL_TIME
    assert job.posted_at == datetime(2026, 8, 25, 10, 30, tzinfo=UTC)
    assert job.application_url.endswith("/jobs/4567")
    assert "0-1 years" in job.description


def test_greenhouse_without_a_publish_date_leaves_posted_at_unset():
    payload = {**GREENHOUSE_PAYLOAD}
    del payload["first_published"]
    del payload["updated_at"]
    assert GreenhouseSource(["example"])._normalize(payload, "example").posted_at is None


def test_lever_normalization():
    job = LeverSource(["example"])._normalize(LEVER_PAYLOAD, "example")
    assert job.external_id == "abc-123"
    assert job.workplace_type is WorkplaceType.REMOTE
    assert job.country == "US"
    assert job.employment_type is EmploymentType.FULL_TIME
    assert job.posted_at is not None
    # The apply URL is preferred over the hosted listing URL.
    assert job.application_url.endswith("/apply")


def test_lever_bad_timestamp_is_not_invented():
    payload = {**LEVER_PAYLOAD, "createdAt": None}
    assert LeverSource(["example"])._normalize(payload, "example").posted_at is None
