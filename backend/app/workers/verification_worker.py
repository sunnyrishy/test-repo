"""Verification and scoring only, for re-running the AI stages on demand."""
from __future__ import annotations

import asyncio
import logging

from app.database import SessionLocal
from app.services.scoring import run_scoring
from app.services.verification import run_verification

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")


async def main() -> None:
    db = SessionLocal()
    try:
        await run_verification(db)
        run_scoring(db)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
