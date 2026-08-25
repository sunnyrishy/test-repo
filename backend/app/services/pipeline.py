"""The end-to-end pipeline, in the order the stages must run."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.services.deduplication import merge_duplicates
from app.services.discovery import run_discovery
from app.services.notification import send_digests
from app.services.scoring import run_scoring
from app.services.verification import run_verification

logger = logging.getLogger(__name__)


async def run_pipeline(
    db: Session, settings: Settings | None = None, notify: bool = True
) -> dict:
    """discover -> merge duplicates -> verify -> score -> notify.

    A failure in a later stage does not discard the work of an earlier one:
    each stage commits before the next begins.
    """
    settings = settings or get_settings()
    results: dict[str, object] = {}

    discovery = await run_discovery(db, settings)
    results["discovery"] = {
        "discovered": discovery.discovered,
        "duplicates": discovery.duplicates,
        "stored": discovery.stored,
        "hard_filter_failures": discovery.hard_filter_failures,
        "passed_filters": discovery.passed_filters,
        "errors": discovery.errors,
    }

    for name, stage in (
        ("deduplication", lambda: merge_duplicates(db)),
        ("verification", None),
        ("scoring", lambda: run_scoring(db, settings)),
    ):
        try:
            if name == "verification":
                results[name] = await run_verification(db, settings)
            else:
                results[name] = stage()
        except Exception as exc:  # noqa: BLE001 - report, never silently discard
            logger.exception("pipeline stage %s failed", name)
            results[name] = {"error": str(exc)}

    if notify:
        try:
            results["notifications"] = send_digests(db, settings)
        except Exception as exc:  # noqa: BLE001
            logger.exception("notification stage failed")
            results["notifications"] = {"error": str(exc)}

    return results
