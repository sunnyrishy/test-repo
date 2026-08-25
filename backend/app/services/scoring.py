"""Scoring (Phase 6): 0-100 for jobs that passed AI verification.

The score orders jobs that are already eligible. It can never make an
ineligible job eligible - score_job() refuses to score anything that is not a
verified PASS, so a "30 years required" role cannot be rescued by a strong
role match.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from app.models import Job, JobVerification
from app.schemas.candidate import CandidateProfileIn
from app.schemas.verification import Decision, SponsorshipStatus, WorkAuthorizationStatus
from app.services.filtering import classify_role

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

WEIGHTS = {
    "role": 20,
    "experience": 20,
    "skill": 15,
    "degree": 10,
    "graduation": 10,
    "work_auth": 10,
    "location": 5,
    "salary": 5,
    "company": 5,
}

WORK_AUTH_FRACTION = {
    WorkAuthorizationStatus.CLEARLY_COMPATIBLE: 1.0,
    WorkAuthorizationStatus.PROBABLY_COMPATIBLE: 0.8,
    # Unknown is common and is not evidence of a problem, so it is not zeroed.
    WorkAuthorizationStatus.UNKNOWN: 0.5,
    WorkAuthorizationStatus.PROBABLY_INCOMPATIBLE: 0.2,
    WorkAuthorizationStatus.CLEARLY_INCOMPATIBLE: 0.0,
}

SPONSORSHIP_BONUS = {
    SponsorshipStatus.AVAILABLE: 1.0,
    SponsorshipStatus.POSSIBLY_AVAILABLE: 0.8,
    SponsorshipStatus.NOT_SPECIFIED: 0.5,
    SponsorshipStatus.NOT_AVAILABLE: 0.0,
    SponsorshipStatus.REQUIRES_CITIZENSHIP: 0.0,
}


@dataclass(slots=True)
class Score:
    role_score: float = 0.0
    experience_score: float = 0.0
    skill_score: float = 0.0
    degree_score: float = 0.0
    graduation_score: float = 0.0
    work_auth_score: float = 0.0
    location_score: float = 0.0
    salary_score: float = 0.0
    company_score: float = 0.0
    overall_score: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


def classify(overall: float) -> str:
    if overall >= 95:
        return "EXCELLENT"
    if overall >= 90:
        return "VERY_STRONG"
    if overall >= 80:
        return "STRONG"
    if overall >= 70:
        return "CONSIDER"
    return "BELOW_THRESHOLD"


def _role_fraction(title: str, profile: CandidateProfileIn) -> float:
    return {"PREFERRED": 1.0, "RELATED": 0.7, "UNRELATED": 0.2, "EXCLUDED": 0.0}[
        classify_role(title, profile)
    ]


def _experience_fraction(verification: JobVerification) -> float:
    required = verification.experience_required
    if required is None:
        return 0.7 if verification.entry_level else 0.5
    if required == 0:
        return 1.0
    if required == 1:
        return 0.9
    # Above the ceiling only survives here when it was preferred, not required.
    return 0.6 if verification.experience_type != "required" else 0.3


def _skill_fraction(verification: JobVerification, profile: CandidateProfileIn) -> float:
    matched = {skill.lower() for skill in verification.matched_skills or []}
    if not matched:
        return 0.3
    # Five relevant skills is treated as a full match; more adds nothing.
    return min(1.0, len(matched & {s.lower() for s in profile.skills}) / 5)


def _salary_fraction(job: Job) -> float:
    top = job.salary_max or job.salary_min
    if top is None:
        # Most postings omit salary; absence must not be punished as if it were low.
        return 0.5
    if top >= 150_000:
        return 1.0
    if top >= 120_000:
        return 0.9
    if top >= 100_000:
        return 0.75
    if top >= 80_000:
        return 0.6
    return 0.4


def _location_fraction(job: Job) -> float:
    return {"Remote": 1.0, "Hybrid": 0.9, "Onsite": 0.7}.get(job.workplace_type or "", 0.6)


def _company_fraction(job: Job) -> float:
    """Deliberately neutral: we have no reputation data, and inventing one
    would be fabricating information. Completeness of the posting is the only
    honest signal available."""
    signals = [bool(job.description), bool(job.application_url), bool(job.posted_at)]
    return 0.5 + 0.5 * (sum(signals) / len(signals))


def score_job(
    job: Job, verification: JobVerification, profile: CandidateProfileIn
) -> Score | None:
    """Score a verified-PASS job. Returns None for anything else."""
    if verification.decision != Decision.PASS.value:
        return None

    work_auth = WorkAuthorizationStatus(verification.work_authorization_status)
    sponsorship = SponsorshipStatus(verification.sponsorship_status)
    work_auth_fraction = max(
        WORK_AUTH_FRACTION[work_auth], SPONSORSHIP_BONUS[sponsorship] * 0.8
    )

    score = Score(
        role_score=WEIGHTS["role"] * _role_fraction(job.title, profile),
        experience_score=WEIGHTS["experience"] * _experience_fraction(verification),
        skill_score=WEIGHTS["skill"] * _skill_fraction(verification, profile),
        degree_score=WEIGHTS["degree"] * (1.0 if verification.degree_match else 0.5),
        graduation_score=WEIGHTS["graduation"]
        * (1.0 if verification.graduation_match else 0.5),
        work_auth_score=WEIGHTS["work_auth"] * work_auth_fraction,
        location_score=WEIGHTS["location"] * _location_fraction(job),
        salary_score=WEIGHTS["salary"] * _salary_fraction(job),
        company_score=WEIGHTS["company"] * _company_fraction(job),
    )
    score.overall_score = round(
        sum(
            getattr(score, f"{key}_score")
            for key in WEIGHTS
        ),
        1,
    )
    return score


def run_scoring(db: "Session", settings=None) -> dict:
    """Score every verified-PASS job whose score is missing or out of date."""
    from sqlalchemy import select

    from app.models import JobScore
    from app.services.profile import get_profile

    profile = get_profile(db)
    rows = db.execute(
        select(Job, JobVerification)
        .join(JobVerification, JobVerification.job_id == Job.id)
        .where(Job.is_active.is_(True), JobVerification.decision == Decision.PASS.value)
    ).all()

    existing = {row.job_id: row for row in db.scalars(select(JobScore)).all()}
    stats = {"scored": 0, "skipped": 0}

    for job, verification in rows:
        score = score_job(job, verification, profile)
        if score is None:
            stats["skipped"] += 1
            continue
        row = existing.get(job.id)
        if row is None:
            row = JobScore(job_id=job.id)
            db.add(row)
        for key, value in score.as_dict().items():
            setattr(row, key, value)
        row.classification = classify(score.overall_score)
        row.verified_at = verification.verified_at
        stats["scored"] += 1

    db.commit()
    logger.info("scoring finished: scored=%d skipped=%d", stats["scored"], stats["skipped"])
    return stats
