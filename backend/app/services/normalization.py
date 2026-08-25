"""Helpers that turn source-specific payloads into the normalized schema.

Rules: never invent a posting date, an application URL, a salary or a location.
Anything the source does not state stays None / UNKNOWN.
"""
from __future__ import annotations

import html
import re
from datetime import UTC, datetime

from dateutil import parser as date_parser

from app.schemas.job import EmploymentType, WorkplaceType

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]*\n[ \t]*")

# Ordered: the first US signal wins, but an explicit non-US country wins over
# a bare state abbreviation appearing inside a longer string.
_US_TOKENS = (
    "united states",
    "usa",
    "u.s.",
    "us-",
    "remote - us",
    "remote, us",
)
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}
_US_CITIES = {
    "new york", "san francisco", "seattle", "boston", "austin", "chicago",
    "los angeles", "san jose", "denver", "atlanta", "dallas", "houston",
    "washington", "pittsburgh", "philadelphia", "san diego", "portland",
}
_NON_US_HINTS = (
    "canada", "united kingdom", "london", "india", "bengaluru", "bangalore",
    "germany", "berlin", "france", "paris", "ireland", "dublin", "australia",
    "singapore", "japan", "tokyo", "netherlands", "amsterdam", "poland",
    "spain", "brazil", "mexico", "israel", "china", "korea", "toronto",
    "vancouver", "montreal",
)

_EMPLOYMENT_ALIASES = {
    "full time": EmploymentType.FULL_TIME,
    "full-time": EmploymentType.FULL_TIME,
    "fulltime": EmploymentType.FULL_TIME,
    "permanent": EmploymentType.FULL_TIME,
    "regular": EmploymentType.FULL_TIME,
    "part time": EmploymentType.PART_TIME,
    "part-time": EmploymentType.PART_TIME,
    "parttime": EmploymentType.PART_TIME,
    "contract": EmploymentType.CONTRACT,
    "contractor": EmploymentType.CONTRACT,
    "temporary": EmploymentType.TEMPORARY,
    "temp": EmploymentType.TEMPORARY,
    "intern": EmploymentType.INTERNSHIP,
    "internship": EmploymentType.INTERNSHIP,
    "co-op": EmploymentType.INTERNSHIP,
    "volunteer": EmploymentType.VOLUNTEER,
}


def strip_html(raw: str | None) -> str | None:
    if not raw:
        return None
    text = _TAG_RE.sub("\n", html.unescape(raw)).replace("\xa0", " ")
    text = _WS_RE.sub("\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() or None


def parse_datetime(raw: str | datetime | None) -> datetime | None:
    """Parse a source timestamp into an aware UTC datetime, or None."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        parsed = raw
    else:
        try:
            parsed = date_parser.parse(str(raw))
        except (ValueError, OverflowError, TypeError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_country(location: str | None) -> str | None:
    """Return "US", a non-US marker, or None when the location is unusable."""
    if not location:
        return None
    text = location.lower()
    if any(hint in text for hint in _NON_US_HINTS):
        return "NON_US"
    if any(token in text for token in _US_TOKENS):
        return "US"
    if any(city in text for city in _US_CITIES):
        return "US"
    for part in re.split(r"[,/|]| - ", location):
        token = part.strip().upper()
        if token in _US_STATES:
            return "US"
    if "remote" in text:
        # "Remote" with no geography is not evidence of a US role.
        return None
    return None


def normalize_workplace_type(*fields: str | None) -> WorkplaceType:
    text = " ".join(f.lower() for f in fields if f)
    if "hybrid" in text:
        return WorkplaceType.HYBRID
    if "remote" in text:
        return WorkplaceType.REMOTE
    if "on-site" in text or "onsite" in text or "in office" in text:
        return WorkplaceType.ONSITE
    return WorkplaceType.UNKNOWN


def normalize_employment_type(*fields: str | None) -> EmploymentType:
    text = " ".join(f.lower() for f in fields if f)
    for alias, value in _EMPLOYMENT_ALIASES.items():
        if alias in text:
            return value
    return EmploymentType.UNKNOWN


def normalize_company(name: str) -> str:
    """Lower-cased company key used for fingerprints, not for display."""
    cleaned = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    cleaned = re.sub(
        r"\b(inc|llc|ltd|corp|corporation|co|company|gmbh|plc|limited)\b", " ", cleaned
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_title(title: str) -> str:
    cleaned = re.sub(r"\([^)]*\)", " ", title.lower())
    cleaned = re.sub(r"[^a-z0-9+# ]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_location(location: str | None) -> str:
    if not location:
        return ""
    cleaned = re.sub(r"[^a-z0-9 ]", " ", location.lower())
    return re.sub(r"\s+", " ", cleaned).strip()
