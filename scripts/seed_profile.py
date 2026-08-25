"""Seed the candidate_profile table from config/candidate_profile.yaml."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import SessionLocal  # noqa: E402
from app.services.profile import load_profile_file, save_profile  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        profile = save_profile(db, load_profile_file())
        print(f"Seeded profile: {profile.degree.level} {profile.degree.field}, "
              f"class of {profile.graduation_year}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
