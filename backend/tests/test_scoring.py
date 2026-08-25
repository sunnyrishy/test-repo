from datetime import UTC, datetime

import pytest

from app.models import Job, JobVerification
from app.schemas.verification import Decision
from app.services.scoring import WEIGHTS, classify, score_job


@pytest.fixture
def job():
    return Job(
        id=1,
        external_id="1",
        source="greenhouse",
        company="ABC Corp",
        title="Software Engineer I",
        location="New York, NY",
        workplace_type="Remote",
        employment_type="FullTime",
        description="Entry level.",
        application_url="https://example.com/apply",
        posted_at=datetime.now(UTC),
        salary_min=110_000,
        salary_max=140_000,
    )


def verification(**overrides) -> JobVerification:
    row = JobVerification(
        job_id=1,
        decision=Decision.PASS.value,
        confidence=0.9,
        role_match=True,
        entry_level=True,
        experience_match=True,
        degree_match=True,
        graduation_match=True,
        location_match=True,
        employment_match=True,
        citizenship_required=False,
        security_clearance_required=False,
        experience_required=0,
        experience_type="required",
        work_authorization_status="CLEARLY_COMPATIBLE",
        sponsorship_status="AVAILABLE",
        matched_skills=["Python", "SQL", "C++", "Java", "Git"],
        missing_skills=[],
        rejection_reasons=[],
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def test_weights_total_one_hundred():
    assert sum(WEIGHTS.values()) == 100


def test_ideal_job_scores_near_the_top(job, profile):
    score = score_job(job, verification(), profile)
    assert 95 <= score.overall_score <= 100
    assert classify(score.overall_score) == "EXCELLENT"


def test_score_never_exceeds_one_hundred(job, profile):
    assert score_job(job, verification(), profile).overall_score <= 100


def test_unverified_job_is_not_scored(job, profile):
    assert score_job(job, verification(decision=Decision.REVIEW.value), profile) is None
    assert score_job(job, verification(decision=Decision.FAIL.value), profile) is None
    assert score_job(job, verification(decision=Decision.ERROR.value), profile) is None


def test_scoring_cannot_rescue_an_excessive_experience_requirement(job, profile):
    """A FAIL is never scored, so a strong role match cannot promote it."""
    failed = verification(decision=Decision.FAIL.value, experience_required=30)
    assert score_job(job, failed, profile) is None


def test_incompatible_work_authorization_lowers_the_score(job, profile):
    strong = score_job(job, verification(), profile).overall_score
    weak = score_job(
        job,
        verification(
            work_authorization_status="CLEARLY_INCOMPATIBLE",
            sponsorship_status="NOT_AVAILABLE",
        ),
        profile,
    ).overall_score
    assert weak < strong


def test_missing_salary_is_not_punished_as_if_it_were_low(job, profile):
    job.salary_min = job.salary_max = None
    unknown = score_job(job, verification(), profile).overall_score
    job.salary_max = 60_000
    low = score_job(job, verification(), profile).overall_score
    assert unknown > low


def test_unknown_sponsorship_still_scores_respectably(job, profile):
    score = score_job(
        job,
        verification(
            work_authorization_status="UNKNOWN", sponsorship_status="NOT_SPECIFIED"
        ),
        profile,
    )
    # Unknown is the common case and must not sink an otherwise strong match.
    assert score.overall_score >= 80


def test_related_role_scores_below_a_preferred_role(job, profile):
    preferred = score_job(job, verification(), profile).overall_score
    job.title = "Cloud Engineer"
    related = score_job(job, verification(), profile).overall_score
    assert related < preferred


def test_classification_boundaries():
    assert classify(96) == "EXCELLENT"
    assert classify(95) == "EXCELLENT"
    assert classify(90) == "VERY_STRONG"
    assert classify(80) == "STRONG"
    assert classify(70) == "CONSIDER"
    assert classify(69.9) == "BELOW_THRESHOLD"
