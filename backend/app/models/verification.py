from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

# JSONB on PostgreSQL, plain JSON elsewhere so the suite runs without a server.
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobVerification(Base):
    """The AI verdict for one job. Nullable booleans mean "undetermined"."""

    __tablename__ = "job_verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), unique=True
    )

    decision: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    role_match: Mapped[bool | None] = mapped_column(Boolean)
    entry_level: Mapped[bool | None] = mapped_column(Boolean)
    experience_match: Mapped[bool | None] = mapped_column(Boolean)
    degree_match: Mapped[bool | None] = mapped_column(Boolean)
    graduation_match: Mapped[bool | None] = mapped_column(Boolean)
    location_match: Mapped[bool | None] = mapped_column(Boolean)
    employment_match: Mapped[bool | None] = mapped_column(Boolean)
    citizenship_required: Mapped[bool | None] = mapped_column(Boolean)
    security_clearance_required: Mapped[bool | None] = mapped_column(Boolean)

    experience_required: Mapped[int | None] = mapped_column(Integer)
    experience_type: Mapped[str | None] = mapped_column(String(24))
    education_required: Mapped[str | None] = mapped_column(Text)

    work_authorization_status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    sponsorship_status: Mapped[str] = mapped_column(String(32), default="NOT_SPECIFIED")

    matched_skills: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    rejection_reasons: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    ai_summary: Mapped[str | None] = mapped_column(Text)

    model: Mapped[str | None] = mapped_column(String(128))
    # Reverification triggers: the job's text and the profile it was judged against.
    content_fingerprint: Mapped[str | None] = mapped_column(String(64))
    profile_fingerprint: Mapped[str | None] = mapped_column(String(64))
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
