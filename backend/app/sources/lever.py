"""Lever public postings API.

Docs: https://github.com/lever/postings-api - documented public JSON endpoint.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import httpx

from app.schemas.job import NormalizedJob
from app.services import normalization as norm
from app.sources.base import JobSourceConnector, SourceConfig, SourceError

logger = logging.getLogger(__name__)

BOARD_URL = "https://api.lever.co/v0/postings/{board}?mode=json"


class LeverSource(JobSourceConnector):
    name = "lever"

    def __init__(self, boards: list[str], config: SourceConfig | None = None) -> None:
        super().__init__(config)
        self.boards = boards

    async def fetch(self) -> list[NormalizedJob]:
        if not self.boards:
            return []
        async with httpx.AsyncClient(headers={"User-Agent": "ai-job-intelligence/0.1"}) as client:
            results = await asyncio.gather(
                *(self._fetch_board(client, board) for board in self.boards),
                return_exceptions=True,
            )
        jobs: list[NormalizedJob] = []
        failures: list[str] = []
        for board, result in zip(self.boards, results, strict=True):
            if isinstance(result, BaseException):
                logger.warning("lever board %s failed: %s", board, result)
                failures.append(board)
                continue
            jobs.extend(result)
        if failures and not jobs:
            raise SourceError(f"lever: every board failed ({', '.join(failures)})")
        return jobs

    async def _fetch_board(
        self, client: httpx.AsyncClient, board: str
    ) -> list[NormalizedJob]:
        payload = await self.get_json(client, BOARD_URL.format(board=board))
        if not isinstance(payload, list):
            raise SourceError(f"lever: unexpected payload for board {board}")
        return [self._normalize(raw, board) for raw in payload]

    def _normalize(self, raw: dict, board: str) -> NormalizedJob:
        categories = raw.get("categories") or {}
        location = categories.get("location")
        commitment = categories.get("commitment")
        workplace = raw.get("workplaceType") or categories.get("allLocations")
        description = norm.strip_html(
            raw.get("descriptionPlain") or raw.get("description")
        )
        url = raw.get("applyUrl") or raw.get("hostedUrl")
        return NormalizedJob(
            external_id=str(raw["id"]),
            source=self.name,
            company=board,
            title=(raw.get("text") or "").strip(),
            location=location,
            country=norm.normalize_country(location),
            workplace_type=norm.normalize_workplace_type(
                workplace if isinstance(workplace, str) else None, location
            ),
            employment_type=norm.normalize_employment_type(
                commitment, raw.get("text"), description
            ),
            description=description,
            application_url=url,
            source_url=raw.get("hostedUrl"),
            posted_at=_from_epoch_ms(raw.get("createdAt")),
            source_updated_at=_from_epoch_ms(raw.get("updatedAt")),
        )


def _from_epoch_ms(value: object) -> datetime | None:
    """Lever timestamps are epoch milliseconds."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC)
