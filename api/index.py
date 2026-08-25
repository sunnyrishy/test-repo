"""Vercel serverless entry point for the API.

The @vercel/python runtime serves the ASGI application exported as `app`, and
vercel.json rewrites every request here so FastAPI still owns the routing.

This project deploys from the repository root rather than backend/ because the
service reads config/candidate_profile.yaml and prompts/job_verification.txt at
runtime; both live outside the backend package.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
