"""AI verification (Phase 5).

Only jobs that survived the deterministic filters get here, and a job is not
re-verified while its description, the profile and the verification are all
unchanged - that is what keeps the model spend proportional to new work.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import Job, JobVerification
from app.schemas.candidate import CandidateProfileIn
from app.schemas.job import FilterStatus
from app.schemas.verification import Decision, VerificationResult
from app.services.ai import AIError, AIProvider, AIRequest, build_provider
from app.services.profile import get_profile

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
# Descriptions are long; sending the whole thing is the point (requirements
# hide at the bottom), but a runaway page is truncated rather than refused.
MAX_DESCRIPTION_CHARS = 20_000


def load_prompt(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return (settings.prompts_path / "job_verification.txt").read_text()


def profile_fingerprint(profile: CandidateProfileIn) -> str:
    """Changes whenever anything the model is told about the candidate changes."""
    payload = json.dumps(profile.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def content_fingerprint(job: Job) -> str:
    payload = "|".join(
        (job.title or "", job.location or "", job.employment_type or "", job.description or "")
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def build_user_prompt(job: Job, profile: CandidateProfileIn) -> str:
    """Everything the model is allowed to reason about, and nothing invented."""
    description = job.description or "(the source provided no description)"
    if len(description) > MAX_DESCRIPTION_CHARS:
        description = description[:MAX_DESCRIPTION_CHARS] + "\n[description truncated]"
    candidate = json.dumps(profile.model_dump(mode="json"), indent=2)
    posted = job.posted_at.isoformat() if job.posted_at else "unknown"
    return (
        f"CANDIDATE PROFILE:\n{candidate}\n\n"
        f"JOB TITLE: {job.title}\n"
        f"COMPANY: {job.company}\n"
        f"LOCATION: {job.location or 'not stated'}\n"
        f"EMPLOYMENT TYPE: {job.employment_type or 'not stated'}\n"
        f"POSTED AT: {posted}\n\n"
        f"FULL JOB DESCRIPTION:\n{description}\n"
    )


def parse_result(raw: str) -> VerificationResult:
    """Parse and validate model output. Raises ValidationError/ValueError."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?|```$", "", text).strip()
    match = _JSON_BLOCK_RE.search(text)
    if match is None:
        raise ValueError("no JSON object in model output")
    return VerificationResult.model_validate(json.loads(match.group(0)))


async def verify_job(
    job: Job,
    profile: CandidateProfileIn,
    provider: AIProvider,
    system_prompt: str,
    settings: Settings,
) -> VerificationResult:
    """Ask the model, retrying invalid output; never return malformed data."""
    request = AIRequest(
        system_prompt=system_prompt,
        user_prompt=build_user_prompt(job, profile),
        max_output_tokens=settings.ai_max_output_tokens,
    )
    last_error: Exception | None = None
    for attempt in range(settings.ai_max_attempts):
        try:
            raw = await provider.complete(request)
            return parse_result(raw)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning(
                "job %s: invalid AI output (attempt %d/%d): %s",
                job.id,
                attempt + 1,
                settings.ai_max_attempts,
                exc,
            )
        except AIError as exc:
            last_error = exc
            logger.warning("job %s: AI call failed (attempt %d): %s", job.id, attempt + 1, exc)
            if attempt < settings.ai_max_attempts - 1:
                await asyncio.sleep(2**attempt)

    # Out of attempts: record the error instead of writing a guess.
    return VerificationResult(
        decision=Decision.ERROR,
        confidence=0.0,
        checks={},
        rejection_reasons=[f"verification_error: {last_error}"],
        summary="Verification failed; the model did not return valid output.",
    )


def needs_verification(
    job: Job, verification: JobVerification | None, profile_hash: str, max_age_days: int
) -> bool:
    """Reverify on changed content, changed profile, or an aged verification."""
    if verification is None:
        return True
    if verification.decision == Decision.ERROR.value:
        return True
    if verification.content_fingerprint != content_fingerprint(job):
        return True
    if verification.profile_fingerprint != profile_hash:
        return True
    verified_at = verification.verified_at
    if verified_at is None:
        return True
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    return datetime.now(UTC) - verified_at > timedelta(days=max_age_days)


def store_result(
    db: Session, job: Job, result: VerificationResult, model: str, profile_hash: str
) -> JobVerification:
    row = db.scalar(select(JobVerification).where(JobVerification.job_id == job.id))
    if row is None:
        row = JobVerification(job_id=job.id)
        db.add(row)

    row.decision = result.decision.value
    row.confidence = result.confidence
    row.role_match = result.checks.role_match
    row.entry_level = result.checks.entry_level
    row.experience_match = result.checks.experience_match
    row.degree_match = result.checks.degree_match
    row.graduation_match = result.checks.graduation_match
    row.location_match = result.checks.location_match
    row.employment_match = result.checks.employment_match
    row.citizenship_required = result.checks.citizenship_required
    row.security_clearance_required = result.checks.security_clearance_required
    row.experience_required = result.experience.required_years
    row.experience_type = result.experience.requirement_type.value
    row.education_required = result.education.required
    row.work_authorization_status = result.work_authorization.status.value
    row.sponsorship_status = result.sponsorship.status.value
    row.matched_skills = result.matched_skills
    row.missing_skills = result.missing_skills
    row.rejection_reasons = result.rejection_reasons
    row.ai_summary = result.summary
    row.model = model
    row.content_fingerprint = content_fingerprint(job)
    row.profile_fingerprint = profile_hash
    row.verified_at = datetime.now(UTC)

    job.last_verified_at = row.verified_at
    return row


async def run_verification(db: Session, settings: Settings | None = None) -> dict:
    """Verify every filter-passing job whose verification is missing or stale."""
    settings = settings or get_settings()
    profile = get_profile(db)
    profile_hash = profile_fingerprint(profile)
    provider = build_provider(settings)
    system_prompt = load_prompt(settings)

    candidates = db.scalars(
        select(Job)
        .where(Job.is_active.is_(True), Job.filter_status == FilterStatus.PASS.value)
        .where(Job.canonical_job_id.is_(None))
        .order_by(Job.first_seen_at.desc())
    ).all()

    existing = {
        row.job_id: row
        for row in db.scalars(select(JobVerification)).all()
    }
    pending = [
        job
        for job in candidates
        if needs_verification(
            job, existing.get(job.id), profile_hash, settings.verification_max_age_days
        )
    ][: settings.verification_batch_size]

    stats = {
        "candidates": len(candidates),
        "verified": 0,
        "cached": len(candidates) - len(pending),
        "passed": 0,
        "failed": 0,
        "review": 0,
        "errors": 0,
    }
    if not pending:
        logger.info("verification: nothing to do (%d cached)", stats["cached"])
        return stats

    semaphore = asyncio.Semaphore(settings.ai_concurrency)

    async def verify_one(job: Job) -> tuple[Job, VerificationResult]:
        async with semaphore:
            return job, await verify_job(job, profile, provider, system_prompt, settings)

    for job, result in await asyncio.gather(*(verify_one(job) for job in pending)):
        store_result(db, job, result, provider.model, profile_hash)
        stats["verified"] += 1
        stats[
            {
                Decision.PASS: "passed",
                Decision.FAIL: "failed",
                Decision.REVIEW: "review",
                Decision.ERROR: "errors",
            }[result.decision]
        ] += 1
    db.commit()

    logger.info(
        "verification finished: verified=%d passed=%d failed=%d review=%d errors=%d cached=%d",
        stats["verified"],
        stats["passed"],
        stats["failed"],
        stats["review"],
        stats["errors"],
        stats["cached"],
    )
    return stats
