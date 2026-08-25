import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.config import Settings
from app.models import Job, JobVerification
from app.schemas.verification import Decision
from app.services.ai import AIError, build_provider
from app.services.ai.base import AIProvider
from app.services.verification import (
    build_user_prompt,
    content_fingerprint,
    needs_verification,
    profile_fingerprint,
    verify_job,
)


@pytest.fixture
def settings():
    return Settings(ai_provider="mock", ai_max_attempts=2, database_url="sqlite://")


@pytest.fixture
def job():
    return Job(
        id=1,
        external_id="1",
        source="greenhouse",
        company="ABC Corp",
        title="Software Engineer I",
        location="New York, NY",
        employment_type="FullTime",
        description="Entry level role. 0-1 years experience.",
        posted_at=datetime.now(UTC),
    )


class BrokenProvider(AIProvider):
    name = "broken"

    def __init__(self):
        super().__init__("", "broken-model")
        self.calls = 0

    async def complete(self, request):
        self.calls += 1
        return "not json at all"


class UnreachableProvider(AIProvider):
    name = "unreachable"

    def __init__(self):
        super().__init__("", "x")
        self.calls = 0

    async def complete(self, request):
        self.calls += 1
        raise AIError("connection refused")


def test_prompt_contains_the_whole_job_and_the_profile(job, profile):
    prompt = build_user_prompt(job, profile)
    for expected in ("Software Engineer I", "ABC Corp", "New York, NY", "FullTime",
                     "0-1 years experience", "graduation_year"):
        assert expected in prompt


def test_prompt_says_unknown_rather_than_inventing_a_date(job, profile):
    job.posted_at = None
    assert "POSTED AT: unknown" in build_user_prompt(job, profile)


def test_invalid_output_is_retried_then_recorded_as_an_error(job, profile, settings):
    provider = BrokenProvider()
    result = asyncio.run(verify_job(job, profile, provider, "system", settings))
    assert provider.calls == settings.ai_max_attempts
    assert result.decision is Decision.ERROR
    assert "verification_error" in result.rejection_reasons[0]


def test_unreachable_provider_yields_an_error_not_a_guess(job, profile, settings):
    result = asyncio.run(verify_job(job, profile, UnreachableProvider(), "system", settings))
    assert result.decision is Decision.ERROR


def test_mock_provider_never_passes_a_job(job, profile, settings):
    result = asyncio.run(
        verify_job(job, profile, build_provider(settings), "system", settings)
    )
    # The mock reasons about nothing, so its jobs land in REVIEW, never PASS.
    assert result.decision is Decision.REVIEW


def test_mock_provider_reads_citizenship_and_clearance(job, profile, settings):
    job.description = "US citizens only. Active security clearance required."
    result = asyncio.run(
        verify_job(job, profile, build_provider(settings), "system", settings)
    )
    assert result.checks.citizenship_required is True
    assert result.checks.security_clearance_required is True
    assert result.decision is Decision.FAIL


def test_unknown_provider_is_rejected():
    with pytest.raises(AIError):
        build_provider(Settings(ai_provider="wishful-thinking", database_url="sqlite://"))


def test_real_provider_requires_a_model():
    with pytest.raises(AIError):
        build_provider(Settings(ai_provider="openai", ai_api_key="k", database_url="sqlite://"))


# --- caching / reverification ---

def _verification(job, profile, **overrides):
    row = JobVerification(
        job_id=job.id,
        decision=Decision.PASS.value,
        content_fingerprint=content_fingerprint(job),
        profile_fingerprint=profile_fingerprint(profile),
        verified_at=datetime.now(UTC),
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def test_unchanged_job_is_not_reverified(job, profile):
    row = _verification(job, profile)
    assert needs_verification(job, row, profile_fingerprint(profile), 7) is False


def test_missing_verification_needs_work(job, profile):
    assert needs_verification(job, None, profile_fingerprint(profile), 7) is True


def test_changed_description_triggers_reverification(job, profile):
    row = _verification(job, profile)
    job.description = "Now requires 10 years of experience."
    assert needs_verification(job, row, profile_fingerprint(profile), 7) is True


def test_changed_profile_triggers_reverification(job, profile):
    row = _verification(job, profile)
    changed = profile.model_copy(update={"graduation_year": 2027})
    assert needs_verification(job, row, profile_fingerprint(changed), 7) is True


def test_stale_verification_is_redone(job, profile):
    row = _verification(job, profile, verified_at=datetime.now(UTC) - timedelta(days=30))
    assert needs_verification(job, row, profile_fingerprint(profile), 7) is True


def test_previous_error_is_retried(job, profile):
    row = _verification(job, profile, decision=Decision.ERROR.value)
    assert needs_verification(job, row, profile_fingerprint(profile), 7) is True
