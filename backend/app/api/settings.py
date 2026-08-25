from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read_settings(settings: Settings = Depends(get_settings)) -> dict:
    """Non-secret runtime configuration. Secrets are never returned."""
    return {
        "job_discovery_interval_minutes": settings.job_discovery_interval_minutes,
        "max_job_age_hours": settings.max_job_age_hours,
        "min_match_score": settings.min_match_score,
        "notification_min_score": settings.notification_min_score,
        "sources": {
            "greenhouse": settings.greenhouse_board_list,
            "lever": settings.lever_board_list,
        },
    }
