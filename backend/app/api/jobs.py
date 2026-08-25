from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.database import get_db
from app.models import DiscoveryRun, Job, JobScore, JobVerification
from app.schemas.job import FilterStatus, JobDetailOut, JobOut, JobPage
from app.schemas.verification import Decision

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# "verified" is the dashboard default: only jobs the AI passed are shown.
DEFAULT_VIEW = "verified"


def _base_query():
    return (
        select(Job)
        .options(
            selectinload(Job.sources),
            selectinload(Job.verification),
            selectinload(Job.score),
        )
        .where(Job.is_active.is_(True), Job.canonical_job_id.is_(None))
    )


def _apply_view(query, view: str):
    """A job reaches the primary dashboard only if it passed verification."""
    if view == "verified":
        return query.join(JobVerification, JobVerification.job_id == Job.id).where(
            JobVerification.decision == Decision.PASS.value
        )
    if view == "review":
        return query.join(JobVerification, JobVerification.job_id == Job.id).where(
            JobVerification.decision == Decision.REVIEW.value
        )
    if view == "filtered":
        return query.where(Job.filter_status == FilterStatus.PASS.value)
    return query


@router.get("", response_model=JobPage)
def list_jobs(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    search: str | None = None,
    status: str | None = None,
    view: str = DEFAULT_VIEW,
    min_score: float | None = None,
    workplace_type: str | None = None,
    work_authorization: str | None = None,
    sponsorship: str | None = None,
    min_salary: int | None = None,
    posted_within_hours: int | None = None,
    sort: str = "score",
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JobPage:
    """Paginated job list. The browser never receives the whole table."""
    query = _apply_view(_base_query(), view)

    if status:
        query = query.where(Job.status == status)
    if workplace_type:
        query = query.where(Job.workplace_type == workplace_type)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            func.lower(Job.title).like(pattern) | func.lower(Job.company).like(pattern)
        )
    if posted_within_hours:
        cutoff = datetime.now(UTC) - timedelta(hours=posted_within_hours)
        query = query.where(Job.posted_at.is_not(None), Job.posted_at >= cutoff)
    if min_salary:
        query = query.where(
            func.coalesce(Job.salary_max, Job.salary_min).is_not(None),
            func.coalesce(Job.salary_max, Job.salary_min) >= min_salary,
        )
    if work_authorization or sponsorship:
        query = query.join(
            JobVerification, JobVerification.job_id == Job.id, isouter=False
        )
        if work_authorization:
            query = query.where(
                JobVerification.work_authorization_status == work_authorization
            )
        if sponsorship:
            query = query.where(JobVerification.sponsorship_status == sponsorship)

    threshold = min_score if min_score is not None else settings.min_match_score
    if sort == "score" or min_score is not None:
        query = query.join(JobScore, JobScore.job_id == Job.id).where(
            JobScore.overall_score >= threshold
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    if sort == "score":
        query = query.order_by(JobScore.overall_score.desc(), Job.posted_at.desc().nullslast())
    elif sort == "company":
        query = query.order_by(Job.company.asc())
    elif sort == "salary":
        query = query.order_by(func.coalesce(Job.salary_max, Job.salary_min).desc().nullslast())
    else:
        query = query.order_by(Job.posted_at.desc().nullslast(), Job.first_seen_at.desc())

    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return JobPage(
        items=[JobOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/top", response_model=list[JobOut])
def top_jobs(
    db: Session = Depends(get_db), limit: int = Query(10, ge=1, le=50)
) -> list[JobOut]:
    rows = db.scalars(
        _apply_view(_base_query(), "verified")
        .join(JobScore, JobScore.job_id == Job.id)
        .order_by(JobScore.overall_score.desc())
        .limit(limit)
    ).all()
    return [JobOut.model_validate(row) for row in rows]


@router.get("/recent", response_model=list[JobOut])
def recent_jobs(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limit: int = Query(10, ge=1, le=50),
) -> list[JobOut]:
    """Verified jobs still inside the freshness window."""
    cutoff = datetime.now(UTC) - timedelta(hours=settings.max_job_age_hours)
    rows = db.scalars(
        _apply_view(_base_query(), "verified")
        .where(Job.posted_at.is_not(None), Job.posted_at >= cutoff)
        .order_by(Job.posted_at.desc())
        .limit(limit)
    ).all()
    return [JobOut.model_validate(row) for row in rows]


@router.get("/stats")
def stats(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    """Funnel counters for the statistics page and for debugging runs."""
    day_ago = datetime.now(UTC) - timedelta(days=1)
    week_ago = datetime.now(UTC) - timedelta(days=7)

    def count(*where) -> int:
        return db.scalar(select(func.count()).select_from(Job).where(*where)) or 0

    by_reason = db.execute(
        select(Job.filter_rejection_reason, func.count())
        .where(Job.filter_rejection_reason.is_not(None))
        .group_by(Job.filter_rejection_reason)
    ).all()
    by_source = db.execute(select(Job.source, func.count()).group_by(Job.source)).all()
    by_decision = db.execute(
        select(JobVerification.decision, func.count()).group_by(JobVerification.decision)
    ).all()
    by_classification = db.execute(
        select(JobScore.classification, func.count()).group_by(JobScore.classification)
    ).all()

    last_run = db.scalar(
        select(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).limit(1)
    )
    decisions = {decision: total for decision, total in by_decision}

    return {
        "discovered_today": count(Job.first_seen_at >= day_ago),
        "discovered_this_week": count(Job.first_seen_at >= week_ago),
        "duplicates_merged": count(Job.canonical_job_id.is_not(None)),
        "passed_filters": count(Job.filter_status == FilterStatus.PASS.value),
        "rejected": count(Job.filter_status == FilterStatus.REJECT.value),
        "verified": sum(decisions.values()),
        "verified_pass": decisions.get(Decision.PASS.value, 0),
        "verified_fail": decisions.get(Decision.FAIL.value, 0),
        "verified_review": decisions.get(Decision.REVIEW.value, 0),
        "verification_errors": decisions.get(Decision.ERROR.value, 0),
        "average_score": db.scalar(select(func.avg(JobScore.overall_score))),
        "excellent_matches": db.scalar(
            select(func.count()).select_from(JobScore).where(JobScore.overall_score >= 95)
        ),
        "min_match_score": settings.min_match_score,
        "by_rejection_reason": {reason: total for reason, total in by_reason},
        "by_source": {source: total for source, total in by_source},
        "by_classification": {name: total for name, total in by_classification},
        "last_run": None
        if last_run is None
        else {
            "started_at": last_run.started_at,
            "finished_at": last_run.finished_at,
            "discovered": last_run.discovered,
            "duplicates": last_run.duplicates,
            "stored": last_run.stored,
            "hard_filter_failures": last_run.hard_filter_failures,
            "passed_filters": last_run.passed_filters,
            "per_source": last_run.per_source,
            "errors": last_run.errors,
        },
    }


@router.get("/{job_id}", response_model=JobDetailOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> Job:
    job = db.scalar(_base_query().where(Job.id == job_id, Job.is_active.is_(True)))
    if job is None:
        # Also serve merged duplicates, so an old link lands on the canonical job.
        duplicate = db.get(Job, job_id)
        if duplicate is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if duplicate.canonical_job_id is None:
            return duplicate
        job = db.scalar(_base_query().where(Job.id == duplicate.canonical_job_id))
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/status")
def set_status(job_id: int, status: str, db: Session = Depends(get_db)) -> dict:
    allowed = {
        "NEW", "SAVED", "APPLY", "APPLIED", "INTERVIEW",
        "OFFER", "REJECTED", "WITHDRAWN", "CLOSED", "HIDDEN",
    }
    if status not in allowed:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(allowed)}")
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = status
    job.status_changed_at = datetime.now(UTC)
    db.commit()
    return {"id": job.id, "status": job.status}
