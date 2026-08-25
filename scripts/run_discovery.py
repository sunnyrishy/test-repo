"""Run one discovery pass from the command line."""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import SessionLocal  # noqa: E402
from app.services.discovery import run_discovery  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")


async def main() -> None:
    db = SessionLocal()
    try:
        await run_discovery(db)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
