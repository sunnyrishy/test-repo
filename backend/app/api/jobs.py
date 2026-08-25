from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.database import get_db
from app.models import DiscoveryRun, Job
from app.schemas.job import FilterStatus, JobDetailOut, JobOut, JobPage

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

SORTS = {
    "newest": (Job.posted_at.desc().nullslast(), Job.first_seen_at.desc()),
    "company": (Job.company.asc(),),
    "salary": (Job.salary_max.desc().nullslast(),),
}


@router.get("", response_model=JobPage)
def list_jobs(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    search: str | None = None,
    status: str | None = None,
    filter_status: str = FilterStatus.PASS.value,
    workplace_type: str | None = None,
    posted_within_hours: int | None = None,
    sort: str = "newest",
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JobPage:
    """Paginated job list. The browser never receives the whole table."""
    query = select(Job).options(selectinload(Job.sources)).where(Job.is_active.is_(True))

    if filter_status != "all":
        query = query.where(Job.filter_status == filter_status)
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

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    for clause in SORTS.get(sort, SORTS["newest"]):
        query = query.order_by(clause)

    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return JobPage(
        items=[JobOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    """Pipeline counters for the statistics page and for debugging runs."""
    day_ago = datetime.now(UTC) - timedelta(days=1)
    week_ago = datetime.now(UTC) - timedelta(days=7)

    by_reason = db.execute(
        select(Job.filter_rejection_reason, func.count())
        .where(Job.filter_rejection_reason.is_not(None))
        .group_by(Job.filter_rejection_reason)
    ).all()
    by_source = db.execute(select(Job.source, func.count()).group_by(Job.source)).all()

    last_run = db.scalar(select(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).limit(1))

    return {
        "discovered_today": db.scalar(
            select(func.count()).select_from(Job).where(Job.first_seen_at >= day_ago)
        ),
        "discovered_this_week": db.scalar(
            select(func.count()).select_from(Job).where(Job.first_seen_at >= week_ago)
        ),
        "passed_filters": db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.filter_status == FilterStatus.PASS.value)
        ),
        "rejected": db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.filter_status == FilterStatus.REJECT.value)
        ),
        "by_rejection_reason": {reason: count for reason, count in by_reason},
        "by_source": {source: count for source, count in by_source},
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
            "errors": last_run.errors,
        },
    }


@router.get("/{job_id}", response_model=JobDetailOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> Job:
    job = db.scalar(select(Job).options(selectinload(Job.sources)).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/status")
def set_status(job_id: int, status: str, db: Session = Depends(get_db)) -> dict:
    allowed = {"NEW", "SAVED", "APPLY", "APPLIED", "INTERVIEW", "REJECTED", "CLOSED"}
    if status not in allowed:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(allowed)}")
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = status
    job.status_changed_at = datetime.now(UTC)
    db.commit()
    return {"id": job.id, "status": job.status}
