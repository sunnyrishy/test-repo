from app.config import Settings
from app.sources.base import JobSourceConnector, SourceConfig
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource


def build_connectors(settings: Settings) -> list[JobSourceConnector]:
    """Instantiate every connector that has been configured with a board."""
    config = SourceConfig(
        timeout_seconds=settings.source_request_timeout_seconds,
        max_retries=settings.source_max_retries,
        rate_limit_per_second=settings.source_rate_limit_per_second,
        concurrency=settings.source_concurrency,
    )
    connectors: list[JobSourceConnector] = []
    if settings.greenhouse_board_list:
        connectors.append(GreenhouseSource(settings.greenhouse_board_list, config))
    if settings.lever_board_list:
        connectors.append(LeverSource(settings.lever_board_list, config))
    return connectors
