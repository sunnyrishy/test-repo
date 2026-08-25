from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.deduplication import merge_duplicates
from app.services.discovery import run_discovery
from app.services.notification import send_digests
from app.services.pipeline import run_pipeline
from app.services.scoring import run_scoring
from app.services.verification import run_verification

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/pipeline/run")
async def trigger_pipeline(db: Session = Depends(get_db), notify: bool = True) -> dict:
    """Run every stage once, on demand. The worker runs this on a schedule."""
    return await run_pipeline(db, notify=notify)


@router.post("/discovery/run")
async def trigger_discovery(db: Session = Depends(get_db)) -> dict:
    stats = await run_discovery(db)
    return {
        "discovered": stats.discovered,
        "duplicates": stats.duplicates,
        "stored": stats.stored,
        "hard_filter_failures": stats.hard_filter_failures,
        "passed_filters": stats.passed_filters,
        "per_source": stats.per_source,
        "errors": stats.errors,
    }


@router.post("/deduplication/run")
def trigger_deduplication(db: Session = Depends(get_db)) -> dict:
    return merge_duplicates(db)


@router.post("/verification/run")
async def trigger_verification(db: Session = Depends(get_db)) -> dict:
    return await run_verification(db)


@router.post("/scoring/run")
def trigger_scoring(db: Session = Depends(get_db)) -> dict:
    return run_scoring(db)


@router.post("/notifications/run")
def trigger_notifications(db: Session = Depends(get_db)) -> dict:
    return send_digests(db)
