"""Application settings. Every threshold here is configurable via environment."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/job_agent"

    # Shared secret for admin routes. Empty means "no auth", which is fine for
    # a local stack and is NOT fine for a hosted one - see app/security.py.
    api_key: str = ""
    # Origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # AI verification. "mock" is for development and tests only; it never
    # fabricates a decision in production because it is not the default.
    ai_provider: str = "mock"
    ai_api_key: str = ""
    ai_model: str = ""
    ai_max_output_tokens: int = 1500
    ai_max_attempts: int = 3
    ai_concurrency: int = 4
    verification_max_age_days: int = 7
    verification_batch_size: int = 50

    # Pipeline thresholds
    job_discovery_interval_minutes: int = 180
    max_job_age_hours: int = 72
    min_match_score: int = 80
    notification_min_score: int = 90

    # Notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    notification_email: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    # Source connectors
    greenhouse_boards: str = ""
    lever_boards: str = ""

    source_request_timeout_seconds: float = 20.0
    source_max_retries: int = 3
    source_rate_limit_per_second: float = 2.0
    source_concurrency: int = 4

    candidate_profile_path: Path = REPO_ROOT / "config" / "candidate_profile.yaml"
    prompts_path: Path = REPO_ROOT / "prompts"

    @property
    def cors_origin_list(self) -> list[str]:
        return _split(self.cors_origins)

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
