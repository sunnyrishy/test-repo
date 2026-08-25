from datetime import UTC, datetime

import pytest

from app.schemas.job import EmploymentType, WorkplaceType
from app.services.normalization import (
    normalize_company,
    normalize_country,
    normalize_employment_type,
    normalize_title,
    normalize_workplace_type,
    parse_datetime,
    strip_html,
)


def test_strip_html_removes_markup_and_entities():
    assert strip_html("<p>Hello&nbsp;<b>World</b></p>") == "Hello\nWorld"


def test_strip_html_of_empty_is_none():
    assert strip_html("") is None


def test_parse_datetime_assumes_utc_for_naive_input():
    assert parse_datetime("2026-08-25T10:30:00") == datetime(2026, 8, 25, 10, 30, tzinfo=UTC)


def test_parse_datetime_returns_none_for_garbage():
    # A date we cannot parse must stay unknown rather than become "now".
    assert parse_datetime("sometime soon") is None
    assert parse_datetime(None) is None


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("New York, NY", "US"),
        ("Remote (United States)", "US"),
        ("Austin, TX / Remote", "US"),
        ("London, United Kingdom", "NON_US"),
        ("Berlin, Germany", "NON_US"),
        ("Remote", None),
        (None, None),
    ],
)
def test_normalize_country(location, expected):
    assert normalize_country(location) == expected


def test_normalize_workplace_type_prefers_hybrid():
    assert normalize_workplace_type("Hybrid - Remote friendly") is WorkplaceType.HYBRID
    assert normalize_workplace_type("Remote, US") is WorkplaceType.REMOTE
    assert normalize_workplace_type("New York") is WorkplaceType.UNKNOWN


def test_normalize_employment_type():
    assert normalize_employment_type("Full-time") is EmploymentType.FULL_TIME
    assert normalize_employment_type(None, "Software Engineer Intern") is EmploymentType.INTERNSHIP
    assert normalize_employment_type("Contractor") is EmploymentType.CONTRACT
    assert normalize_employment_type("") is EmploymentType.UNKNOWN


def test_company_and_title_normalization():
    assert normalize_company("Example Company, Inc.") == "example"
    assert normalize_title("Software Engineer I (New Grad)") == "software engineer i"
