from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.services.notification import configured_channels

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read_settings(settings: Settings = Depends(get_settings)) -> dict:
    """Non-secret runtime configuration. Secrets are never returned."""
    return {
        "job_discovery_interval_minutes": settings.job_discovery_interval_minutes,
        "max_job_age_hours": settings.max_job_age_hours,
        "min_match_score": settings.min_match_score,
        "notification_min_score": settings.notification_min_score,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model or None,
        "verification_max_age_days": settings.verification_max_age_days,
        "notification_channels": sorted(configured_channels(settings)),
        "sources": {
            "greenhouse": settings.greenhouse_board_list,
            "lever": settings.lever_board_list,
        },
    }
