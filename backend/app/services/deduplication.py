"""Phase 4 groundwork: a stable fingerprint for every normalized job.

Full canonical-job merging (requisition IDs, semantic similarity) is Phase 4;
what exists today is the fingerprint plus exact source+external_id matching,
which is what the ingestion path needs to avoid storing the same posting twice.
"""
from __future__ import annotations

import hashlib

from app.schemas.job import NormalizedJob
from app.services import normalization as norm


def fingerprint(job: NormalizedJob) -> str:
    """company + title + location, normalized, hashed."""
    key = "|".join(
        (
            norm.normalize_company(job.company),
            norm.normalize_title(job.title),
            norm.normalize_location(job.location),
        )
    )
    return hashlib.sha256(key.encode()).hexdigest()[:32]
