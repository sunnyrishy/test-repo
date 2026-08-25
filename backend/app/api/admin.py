from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.discovery import run_discovery

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/discovery/run")
async def trigger_discovery(db: Session = Depends(get_db)) -> dict:
    """Run the pipeline once, on demand. The worker runs it on a schedule."""
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
