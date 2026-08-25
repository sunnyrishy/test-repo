from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EmploymentType(StrEnum):
    FULL_TIME = "FullTime"
    PART_TIME = "PartTime"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"
    TEMPORARY = "Temporary"
    VOLUNTEER = "Volunteer"
    UNKNOWN = "Unknown"


class WorkplaceType(StrEnum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "Onsite"
    UNKNOWN = "Unknown"


class FreshnessStatus(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class FilterStatus(StrEnum):
    PENDING = "PENDING"
    PASS = "PASS"
    REJECT = "REJECT"


class NormalizedJob(BaseModel):
    """The single internal representation every source must produce."""

    external_id: str
    source: str
    company: str
    title: str
    location: str | None = None
    country: str | None = None
    workplace_type: WorkplaceType = WorkplaceType.UNKNOWN
    employment_type: EmploymentType = EmploymentType.UNKNOWN
    description: str | None = None
    application_url: str | None = None
    source_url: str | None = None

    # None when the source does not publish an employer posting date. Never
    # substitute the time we happened to see the job.
    posted_at: datetime | None = None
    source_updated_at: datetime | None = None

    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None


class JobSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    source_url: str | None
    application_url: str | None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    company: str
    title: str
    location: str | None
    country: str | None
    workplace_type: str | None
    employment_type: str | None
    application_url: str | None
    source_url: str | None
    posted_at: datetime | None
    first_seen_at: datetime
    freshness_status: str
    salary_min: int | None
    salary_max: int | None
    currency: str | None
    filter_status: str
    filter_rejection_reason: str | None
    status: str
    sources: list[JobSourceOut] = Field(default_factory=list)


class JobDetailOut(JobOut):
    description: str | None


class JobPage(BaseModel):
    items: list[JobOut]
    total: int
    limit: int
    offset: int
