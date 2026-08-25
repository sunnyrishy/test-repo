"""API authentication.

Local docker-compose runs are private, so auth is optional there. A hosted
deployment is not private: without a key, anyone who finds the URL could
trigger pipeline runs and spend the account's model budget. Set API_KEY in the
hosted environment and the admin routes require it.
"""
from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


def require_admin(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Guard for write/admin routes.

    With no API_KEY configured the guard is inert, which keeps local
    development frictionless. Once a key is set, every admin call must present
    it - as X-API-Key, or as a bearer token so Vercel Cron's
    Authorization header works unchanged.
    """
    if not settings.api_key:
        return

    presented = x_api_key
    if presented is None and authorization and authorization.startswith("Bearer "):
        presented = authorization.removeprefix("Bearer ").strip()

    # Constant-time comparison: a timing side channel would leak the key.
    if presented is None or not hmac.compare_digest(presented, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
