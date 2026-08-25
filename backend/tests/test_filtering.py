from datetime import UTC, datetime, timedelta

import pytest

from app.schemas.job import EmploymentType, FreshnessStatus
from app.services.filtering import (
    classify_role,
    clearly_requires_more_than,
    contains_excluded_seniority,
    freshness_status,
    hard_filter,
    parse_experience_mentions,
)


# --- date filtering ---

def test_recent_posting_is_fresh():
    assert freshness_status(datetime.now(UTC) - timedelta(hours=4), 72) is FreshnessStatus.FRESH


def test_old_posting_is_stale():
    assert freshness_status(datetime.now(UTC) - timedelta(hours=80), 72) is FreshnessStatus.STALE


def test_missing_date_is_unknown_not_fresh():
    assert freshness_status(None, 72) is FreshnessStatus.UNKNOWN


def test_naive_datetime_is_treated_as_utc():
    naive = (datetime.now(UTC) - timedelta(hours=1)).replace(tzinfo=None)
    assert freshness_status(naive, 72) is FreshnessStatus.FRESH


def test_stale_job_rejected(make_job, profile):
    job = make_job(posted_at=datetime.now(UTC) - timedelta(days=9))
    assert hard_filter(job, profile).reason == "OLDER_THAN_MAX_AGE"


def test_unknown_date_allowed_by_default(make_job, profile):
    assert hard_filter(make_job(posted_at=None), profile).passed


def test_unknown_date_rejected_when_disallowed(make_job, profile):
    result = hard_filter(make_job(posted_at=None), profile, allow_unknown_freshness=False)
    assert result.reason == "POSTING_DATE_UNKNOWN"


# --- seniority filtering ---

@pytest.mark.parametrize(
    "title",
    [
        "Senior Software Engineer",
        "Staff Software Engineer",
        "Principal Engineer",
        "Engineering Manager",
        "Director of Engineering",
        "Sr. Software Developer",
        "Software Architect",
        "Lead Backend Engineer",
    ],
)
def test_senior_titles_rejected(make_job, profile, title):
    assert hard_filter(make_job(title=title), profile).reason == "SENIORITY_TOO_HIGH"


@pytest.mark.parametrize(
    "title", ["Software Engineer I", "Backend Engineer, New Grad", "Associate Software Engineer"]
)
def test_entry_titles_survive_seniority_check(profile, title):
    assert contains_excluded_seniority(title, profile.excluded_seniority_terms) is None


def test_seniority_matches_whole_words_only(profile):
    # "Leadership" contains "lead" but is not a lead role.
    assert contains_excluded_seniority(
        "Software Engineer, Leadership Development Program", profile.excluded_seniority_terms
    ) is None


# --- experience parsing ---

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Must have 2+ years of experience", True),
        ("Minimum of 3 years experience required", True),
        ("Requires five years of professional experience", True),
        ("3-5 years required", True),
        ("0-2 years preferred", False),
        ("2 years of experience preferred", False),
        ("Experience with Python is a plus; 4 years ideally", False),
        ("0-1 years of experience", False),
        ("Internship experience is nice to have", False),
        ("", False),
    ],
)
def test_required_experience_detection(text, expected):
    assert clearly_requires_more_than(text, 1) is expected


def test_experience_mentions_capture_required_flag():
    mentions = parse_experience_mentions("Required: 3 years of Java. 5 years preferred.")
    assert [(m.minimum_years, m.is_required) for m in mentions] == [(3, True), (5, False)]


def test_excessive_experience_rejected(make_job, profile):
    job = make_job(description="We require at least 8 years of backend experience.")
    assert hard_filter(job, profile).reason == "EXPERIENCE_TOO_HIGH"


def test_thirty_years_never_passes(make_job, profile):
    job = make_job(description="Must have 30 years of experience.")
    assert not hard_filter(job, profile).passed


# --- location filtering ---

@pytest.mark.parametrize(
    "location", ["New York, NY", "Remote - US", "San Francisco, CA", "United States"]
)
def test_us_locations_pass(make_job, profile, location):
    from app.services.normalization import normalize_country

    job = make_job(location=location, country=normalize_country(location))
    assert hard_filter(job, profile).passed


@pytest.mark.parametrize("location", ["London, United Kingdom", "Bangalore, India", "Toronto, Canada"])
def test_non_us_locations_rejected(make_job, profile, location):
    from app.services.normalization import normalize_country

    job = make_job(location=location, country=normalize_country(location))
    assert hard_filter(job, profile).reason == "NOT_US"


def test_bare_remote_is_undetermined_not_us(make_job, profile):
    from app.services.normalization import normalize_country

    job = make_job(location="Remote", country=normalize_country("Remote"))
    assert hard_filter(job, profile).reason == "LOCATION_UNDETERMINED"


# --- employment filtering ---

def test_internship_rejected(make_job, profile):
    job = make_job(title="Software Engineer Intern", employment_type=EmploymentType.INTERNSHIP)
    assert hard_filter(job, profile).reason == "INTERNSHIP"


@pytest.mark.parametrize(
    "employment", [EmploymentType.PART_TIME, EmploymentType.CONTRACT, EmploymentType.TEMPORARY]
)
def test_non_full_time_rejected(make_job, profile, employment):
    assert hard_filter(make_job(employment_type=employment), profile).reason == "NOT_FULL_TIME"


def test_unknown_employment_type_is_not_a_rejection(make_job, profile):
    # The description may still say; that is AI verification's job, not ours.
    assert hard_filter(make_job(employment_type=EmploymentType.UNKNOWN), profile).passed


# --- role classification ---

@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Software Engineer", "PREFERRED"),
        ("Backend Engineer", "PREFERRED"),
        ("Platform Engineer", "RELATED"),
        ("Machine Learning Engineer", "RELATED"),
        ("Systems Engineer", "RELATED"),
        ("Product Manager", "EXCLUDED"),
        ("Sales Engineer", "EXCLUDED"),
        ("Registered Nurse", "UNRELATED"),
    ],
)
def test_role_classification(profile, title, expected):
    assert classify_role(title, profile) == expected


def test_excluded_role_rejected(make_job, profile):
    assert hard_filter(make_job(title="Technical Program Manager"), profile).reason in {
        "SENIORITY_TOO_HIGH",
        "ROLE_EXCLUDED",
    }


def test_unrelated_role_rejected(make_job, profile):
    assert hard_filter(make_job(title="Marketing Associate"), profile).reason == "ROLE_UNRELATED"


# --- happy path ---

def test_entry_level_us_full_time_job_passes(make_job, profile):
    job = make_job(
        title="Software Engineer I",
        description="0-1 years of experience. BS/MS in Computer Science. 2026 graduates welcome.",
    )
    assert hard_filter(job, profile).passed
