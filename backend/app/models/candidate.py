from datetime import datetime

from sqlalchemy import JSON, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

# JSONB on PostgreSQL, plain JSON elsewhere so the suite runs without a server.
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CandidateProfile(Base):
    """Single-row table holding the editable candidate profile."""

    __tablename__ = "candidate_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_json: Mapped[dict] = mapped_column(JSON_TYPE)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
