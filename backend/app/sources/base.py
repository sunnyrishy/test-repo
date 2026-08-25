"""Source connector interface.

Every connector fetches raw postings from one origin and normalizes them.
Connectors must respect the origin's terms, rate limits and authentication; none
of them may implement bypasses for anti-bot, CAPTCHA or access controls.
"""
from __future__ import annotations

import abc
import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.schemas.job import NormalizedJob

logger = logging.getLogger(__name__)


class SourceError(RuntimeError):
    """A connector failed. The pipeline records it and continues."""


@dataclass(slots=True)
class SourceConfig:
    timeout_seconds: float = 20.0
    max_retries: int = 3
    rate_limit_per_second: float = 2.0
    concurrency: int = 4


class RateLimiter:
    """Minimum-interval limiter shared by all requests of one connector."""

    def __init__(self, per_second: float) -> None:
        self._interval = 1.0 / per_second if per_second > 0 else 0.0
        self._lock = asyncio.Lock()
        self._next_at = 0.0

    async def acquire(self) -> None:
        if not self._interval:
            return
        async with self._lock:
            wait = self._next_at - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._next_at = time.monotonic() + self._interval


class JobSourceConnector(abc.ABC):
    name: str

    def __init__(self, config: SourceConfig | None = None) -> None:
        self.config = config or SourceConfig()
        self._limiter = RateLimiter(self.config.rate_limit_per_second)
        self._semaphore = asyncio.Semaphore(self.config.concurrency)

    @abc.abstractmethod
    async def fetch(self) -> list[NormalizedJob]:
        """Return every posting this connector can see, already normalized."""

    async def get_json(self, client: httpx.AsyncClient, url: str) -> dict | list:
        """GET with rate limiting and exponential backoff on transient errors."""
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            await self._limiter.acquire()
            try:
                async with self._semaphore:
                    response = await client.get(url, timeout=self.config.timeout_seconds)
                if response.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(
                        f"{response.status_code} from {url}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt == self.config.max_retries - 1:
                    break
                backoff = 2**attempt
                logger.warning(
                    "%s: %s (attempt %d/%d), retrying in %ss",
                    self.name,
                    exc,
                    attempt + 1,
                    self.config.max_retries,
                    backoff,
                )
                await asyncio.sleep(backoff)
        raise SourceError(f"{self.name}: GET {url} failed: {last_error}") from last_error
