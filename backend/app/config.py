"""Application settings. Every threshold here is configurable via environment."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/job_agent"

    # Pipeline thresholds
    job_discovery_interval_minutes: int = 180
    max_job_age_hours: int = 72
    min_match_score: int = 80
    notification_min_score: int = 90

    # Source connectors
    greenhouse_boards: str = ""
    lever_boards: str = ""

    source_request_timeout_seconds: float = 20.0
    source_max_retries: int = 3
    source_rate_limit_per_second: float = 2.0
    source_concurrency: int = 4

    candidate_profile_path: Path = REPO_ROOT / "config" / "candidate_profile.yaml"

    @property
    def greenhouse_board_list(self) -> list[str]:
        return _split(self.greenhouse_boards)

    @property
    def lever_board_list(self) -> list[str]:
        return _split(self.lever_boards)


def _split(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
