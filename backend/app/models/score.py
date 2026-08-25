from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobScore(Base):
    """0-100 relevance score for a verified-PASS job."""

    __tablename__ = "job_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), unique=True
    )

    role_score: Mapped[float] = mapped_column(Float, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, default=0.0)
    skill_score: Mapped[float] = mapped_column(Float, default=0.0)
    degree_score: Mapped[float] = mapped_column(Float, default=0.0)
    graduation_score: Mapped[float] = mapped_column(Float, default=0.0)
    work_auth_score: Mapped[float] = mapped_column(Float, default=0.0)
    location_score: Mapped[float] = mapped_column(Float, default=0.0)
    salary_score: Mapped[float] = mapped_column(Float, default=0.0)
    company_score: Mapped[float] = mapped_column(Float, default=0.0)

    overall_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    classification: Mapped[str] = mapped_column(String(24), default="BELOW_THRESHOLD")

    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Notification(Base):
    """One row per job per channel, so a job is never notified about twice."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(32))
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
