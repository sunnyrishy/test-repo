from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    """A canonical job posting, normalized from one or more sources."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
        Index("ix_jobs_fingerprint", "fingerprint"),
        Index("ix_jobs_posted_at", "posted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    external_id: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(64))

    company: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512))
    location: Mapped[str | None] = mapped_column(String(512))
    country: Mapped[str | None] = mapped_column(String(8))
    workplace_type: Mapped[str | None] = mapped_column(String(32))
    employment_type: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)

    application_url: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    # Distinct dates - see docs/architecture.md. posted_at is the employer's date
    # when the source provides one; it is NEVER backfilled from first_seen_at.
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    freshness_status: Mapped[str] = mapped_column(String(16), default="UNKNOWN")

    salary_min: Mapped[int | None] = mapped_column(BigInteger)
    salary_max: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(String(8))

    fingerprint: Mapped[str | None] = mapped_column(String(128))
    canonical_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL")
    )

    # Deterministic filter outcome (Phase 3). AI verification lands in Phase 5.
    filter_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    filter_rejection_reason: Mapped[str | None] = mapped_column(String(64))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(16), default="NEW")
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sources: Mapped[list["JobSource"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    verification: Mapped["JobVerification | None"] = relationship(
        "JobVerification", cascade="all, delete-orphan", uselist=False
    )
    score: Mapped["JobScore | None"] = relationship(
        "JobScore", cascade="all, delete-orphan", uselist=False
    )


class JobSource(Base):
    """Every place a canonical job was seen, so the UI can link all of them."""

    __tablename__ = "job_sources"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_job_sources_source_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))

    source: Mapped[str] = mapped_column(String(64))
    source_job_id: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    application_url: Mapped[str | None] = mapped_column(Text)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job: Mapped[Job] = relationship(back_populates="sources")


class DiscoveryRun(Base):
    """One execution of the discovery pipeline, for the statistics page."""

    __tablename__ = "discovery_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    discovered: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    stored: Mapped[int] = mapped_column(Integer, default=0)
    hard_filter_failures: Mapped[int] = mapped_column(Integer, default=0)
    passed_filters: Mapped[int] = mapped_column(Integer, default=0)

    # {"greenhouse": {"found": 120}, "lever": {"error": "timeout"}}
    per_source: Mapped[str | None] = mapped_column(Text)
    errors: Mapped[str | None] = mapped_column(Text)
