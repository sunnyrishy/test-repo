import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.candidate import CandidateProfileIn  # noqa: E402
from app.schemas.job import EmploymentType, NormalizedJob  # noqa: E402
from app.services.profile import load_profile_file  # noqa: E402


@pytest.fixture(scope="session")
def profile() -> CandidateProfileIn:
    return load_profile_file()


@pytest.fixture
def make_job():
    def _make(**overrides) -> NormalizedJob:
        defaults = dict(
            external_id="1",
            source="greenhouse",
            company="Example Co",
            title="Software Engineer I",
            location="New York, NY",
            country="US",
            employment_type=EmploymentType.FULL_TIME,
            description="Software engineering role for new graduates.",
            posted_at=datetime.now(UTC) - timedelta(hours=4),
        )
        defaults.update(overrides)
        return NormalizedJob(**defaults)

    return _make
