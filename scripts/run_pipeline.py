"""Run the whole pipeline once from the command line."""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import SessionLocal  # noqa: E402
from app.services.pipeline import run_pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")


async def main() -> None:
    db = SessionLocal()
    try:
        results = await run_pipeline(db, notify=False)
        print(json.dumps(results, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
