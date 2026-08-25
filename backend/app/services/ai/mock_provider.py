"""Deterministic stand-in for a real model. Development and tests only.

It performs no reasoning: it reports what it can read literally from the text
and leaves everything else UNKNOWN, so a job verified by this provider lands in
REVIEW rather than being waved through. Selecting it is explicit
(AI_PROVIDER=mock) and every verification it produces is stored with
model="mock" so its output is never mistaken for a real judgement.
"""
from __future__ import annotations

import json
import re

from app.services.ai.base import AIProvider, AIRequest

_CITIZENSHIP_RE = re.compile(
    r"(u\.?s\.?\s+citizens?\s+only|must be a u\.?s\.? citizen|citizenship (is )?required)",
    re.IGNORECASE,
)
_CLEARANCE_RE = re.compile(
    r"(active\s+)?(security\s+)?clearance\s+(is\s+)?required|ts/sci", re.IGNORECASE
)
_NO_SPONSOR_RE = re.compile(
    r"(will not|unable to|do not|does not|cannot)\s+(provide\s+|offer\s+)?sponsor",
    re.IGNORECASE,
)
_SPONSOR_RE = re.compile(r"sponsorship (is )?available|we sponsor", re.IGNORECASE)


class MockProvider(AIProvider):
    name = "mock"

    async def complete(self, request: AIRequest) -> str:
        text = request.user_prompt
        citizenship = bool(_CITIZENSHIP_RE.search(text))
        clearance = bool(_CLEARANCE_RE.search(text))

        if _NO_SPONSOR_RE.search(text):
            sponsorship = "NOT_AVAILABLE"
            work_auth = "PROBABLY_INCOMPATIBLE"
        elif _SPONSOR_RE.search(text):
            sponsorship = "AVAILABLE"
            work_auth = "CLEARLY_COMPATIBLE"
        elif citizenship:
            sponsorship = "REQUIRES_CITIZENSHIP"
            work_auth = "CLEARLY_INCOMPATIBLE"
        else:
            sponsorship = "NOT_SPECIFIED"
            work_auth = "UNKNOWN"

        return json.dumps(
            {
                "decision": "REVIEW",
                "confidence": 0.3,
                "checks": {
                    # Only what a literal read supports; the rest stays unknown.
                    "citizenship_required": citizenship,
                    "security_clearance_required": clearance,
                    "role_match": None,
                    "entry_level": None,
                    "experience_match": None,
                    "degree_match": None,
                    "graduation_match": None,
                    "location_match": None,
                    "employment_match": None,
                },
                "work_authorization": {"status": work_auth, "confidence": 0.3},
                "sponsorship": {"status": sponsorship},
                "rejection_reasons": [],
                "summary": "Mock provider: no semantic verification was performed.",
            }
        )
