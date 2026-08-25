"""Deterministic filters. No LLM call is made for anything decidable here.

Each check returns a machine-readable rejection reason so the statistics page
can show why jobs were dropped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.schemas.job import (
    EmploymentType,
    FilterStatus,
    FreshnessStatus,
    NormalizedJob,
)
from app.schemas.candidate import CandidateProfileIn


@dataclass(slots=True)
class FilterResult:
    status: FilterStatus
    reason: str | None = None

    @property
    def passed(self) -> bool:
        return self.status is FilterStatus.PASS


PASS = FilterResult(FilterStatus.PASS)


def _reject(reason: str) -> FilterResult:
    return FilterResult(FilterStatus.REJECT, reason)


# --- freshness ---------------------------------------------------------------

def freshness_status(posted_at: datetime | None, max_age_hours: int) -> FreshnessStatus:
    """UNKNOWN when the source gave us no employer posting date.

    An unknown date is never presented as fresh, and never invented.
    """
    if posted_at is None:
        return FreshnessStatus.UNKNOWN
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=UTC)
    age = datetime.now(UTC) - posted_at
    if age <= timedelta(hours=max_age_hours):
        return FreshnessStatus.FRESH
    return FreshnessStatus.STALE


# --- seniority ---------------------------------------------------------------

def contains_excluded_seniority(title: str, terms: list[str]) -> str | None:
    """Match seniority terms as whole words so "Leadership" or "Senior" inside
    another word does not trigger, but "Sr." does."""
    haystack = title.lower()
    for term in terms:
        pattern = r"(?<![a-z])" + re.escape(term.lower()).replace(r"\ ", r"\s+")
        pattern += r"(?![a-z])"
        if re.search(pattern, haystack):
            return term
    return None


# --- experience --------------------------------------------------------------

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
# "3+ years", "3-5 years", "3 to 5 years", "minimum of 3 years", "three years"
_EXPERIENCE_RE = re.compile(
    r"(?P<low>\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")"
    r"\s*(?:\+|plus)?\s*"
    r"(?:(?:-|–|—|to)\s*(?P<high>\d{1,2})\s*\+?\s*)?"
    r"(?:\+\s*)?(?:years?|yrs?)",
    re.IGNORECASE,
)
_PREFERRED_MARKERS = (
    "preferred", "prefer ", "nice to have", "nice-to-have", "a plus", "bonus",
    "ideally", "desirable", "desired", "we'd love", "would be great",
)
_REQUIRED_MARKERS = (
    "required", "must have", "must possess", "minimum", "at least", "requires",
    "requirement", "you have", "you bring", "qualifications",
)


@dataclass(slots=True)
class ExperienceMention:
    minimum_years: int
    is_required: bool
    snippet: str


_SEGMENT_RE = re.compile(r"[.;\n\u2022!?]+")


def parse_experience_mentions(description: str | None) -> list[ExperienceMention]:
    """Extract every "N years" mention with the required/preferred distinction.

    "0-2 years preferred" and "2+ years required" mean different things, so each
    mention is judged by the marker words in its own clause - a wider window
    would let a neighbouring sentence's "preferred" soften a hard requirement.
    """
    if not description:
        return []
    mentions: list[ExperienceMention] = []
    for segment in _SEGMENT_RE.split(description):
        context = segment.lower()
        preferred = any(marker in context for marker in _PREFERRED_MARKERS)
        required = any(marker in context for marker in _REQUIRED_MARKERS)
        for match in _EXPERIENCE_RE.finditer(segment):
            raw_low = match.group("low").lower()
            low = _NUMBER_WORDS.get(raw_low) or int(raw_low)
            mentions.append(
                ExperienceMention(
                    minimum_years=low,
                    # A preferred marker wins: "5 years preferred" is not a bar.
                    is_required=required and not preferred,
                    snippet=segment.strip(),
                )
            )
    return mentions


def clearly_requires_more_than(description: str | None, max_years: int) -> bool:
    """True only when a REQUIRED mention exceeds the candidate's ceiling."""
    return any(
        mention.is_required and mention.minimum_years > max_years
        for mention in parse_experience_mentions(description)
    )


# --- role --------------------------------------------------------------------

def classify_role(title: str, profile: CandidateProfileIn) -> str:
    """PREFERRED / RELATED / EXCLUDED / UNRELATED for a job title.

    Deterministic phrase matching only. Genuine semantic matching is an AI
    concern and happens in the verification stage (Phase 5).
    """
    normalized = re.sub(r"[^a-z0-9+# ]", " ", title.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    def matches(role: str) -> bool:
        return re.search(
            r"(?<![a-z])" + re.escape(role.lower()).replace(r"\ ", r"\s+") + r"(?![a-z])",
            normalized,
        ) is not None

    if any(matches(role) for role in profile.excluded_roles):
        return "EXCLUDED"
    if any(matches(role) for role in profile.preferred_roles):
        return "PREFERRED"
    if any(matches(role) for role in profile.related_roles):
        return "RELATED"
    # Catch-all for engineer/developer titles the profile did not enumerate.
    if re.search(r"\b(software|developer|engineer)\b", normalized):
        return "RELATED"
    return "UNRELATED"


# --- pipeline ----------------------------------------------------------------

def hard_filter(
    job: NormalizedJob,
    profile: CandidateProfileIn,
    max_age_hours: int = 72,
    allow_unknown_freshness: bool = True,
) -> FilterResult:
    """Run every cheap check. First failure wins."""
    freshness = freshness_status(job.posted_at, max_age_hours)
    if freshness is FreshnessStatus.STALE:
        return _reject("OLDER_THAN_MAX_AGE")
    if freshness is FreshnessStatus.UNKNOWN and not allow_unknown_freshness:
        return _reject("POSTING_DATE_UNKNOWN")

    allowed_employment = {t.lower() for t in profile.employment_types}
    if job.employment_type is EmploymentType.UNKNOWN:
        # Unknown is not a rejection: AI verification reads the description.
        pass
    elif job.employment_type.value.lower() not in allowed_employment:
        if job.employment_type is EmploymentType.INTERNSHIP:
            return _reject("INTERNSHIP")
        return _reject("NOT_FULL_TIME")

    if job.country == "NON_US":
        return _reject("NOT_US")
    if job.country != profile.country:
        return _reject("LOCATION_UNDETERMINED")

    if contains_excluded_seniority(job.title, profile.excluded_seniority_terms):
        return _reject("SENIORITY_TOO_HIGH")

    role = classify_role(job.title, profile)
    if role == "EXCLUDED":
        return _reject("ROLE_EXCLUDED")
    if role == "UNRELATED":
        return _reject("ROLE_UNRELATED")

    if clearly_requires_more_than(job.description, profile.experience.maximum_preferred_years):
        return _reject("EXPERIENCE_TOO_HIGH")

    return PASS
