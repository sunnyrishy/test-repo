"""Greenhouse public job board API.

Docs: https://developers.greenhouse.io/job-board.html - a documented public
endpoint, no authentication and no scraping required.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from app.schemas.job import NormalizedJob
from app.services import normalization as norm
from app.sources.base import JobSourceConnector, SourceConfig, SourceError

logger = logging.getLogger(__name__)

BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"


class GreenhouseSource(JobSourceConnector):
    name = "greenhouse"

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
                logger.warning("greenhouse board %s failed: %s", board, result)
                failures.append(board)
                continue
            jobs.extend(result)
        if failures and not jobs:
            raise SourceError(f"greenhouse: every board failed ({', '.join(failures)})")
        return jobs

    async def _fetch_board(
        self, client: httpx.AsyncClient, board: str
    ) -> list[NormalizedJob]:
        payload = await self.get_json(client, BOARD_URL.format(board=board))
        if not isinstance(payload, dict):
            raise SourceError(f"greenhouse: unexpected payload for board {board}")
        return [self._normalize(raw, board) for raw in payload.get("jobs", [])]

    def _normalize(self, raw: dict, board: str) -> NormalizedJob:
        location = (raw.get("location") or {}).get("name")
        description = norm.strip_html(raw.get("content"))
        company = (raw.get("company_name") or board).strip()
        url = raw.get("absolute_url")
        metadata = " ".join(
            str(item.get("value"))
            for item in raw.get("metadata") or []
            if item.get("value")
        )
        return NormalizedJob(
            external_id=str(raw["id"]),
            source=self.name,
            company=company,
            title=(raw.get("title") or "").strip(),
            location=location,
            country=norm.normalize_country(location),
            workplace_type=norm.normalize_workplace_type(location, metadata),
            employment_type=norm.normalize_employment_type(
                metadata, raw.get("title"), description
            ),
            description=description,
            application_url=url,
            source_url=url,
            posted_at=norm.parse_datetime(raw.get("first_published") or raw.get("updated_at")),
            source_updated_at=norm.parse_datetime(raw.get("updated_at")),
        )
