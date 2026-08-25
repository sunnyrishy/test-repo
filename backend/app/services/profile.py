"""Loading and persisting the candidate profile.

Business logic reads the profile through these helpers; candidate details are
never written into the code itself.
"""
from __future__ import annotations

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CandidateProfile
from app.schemas.candidate import CandidateProfileIn


def load_profile_file() -> CandidateProfileIn:
    """Read the bootstrap profile from config/candidate_profile.yaml."""
    path = get_settings().candidate_profile_path
    with path.open() as handle:
        return CandidateProfileIn.model_validate(yaml.safe_load(handle))


def get_profile(db: Session) -> CandidateProfileIn:
    """Return the stored profile, seeding it from the YAML file on first use."""
    row = db.scalar(select(CandidateProfile).limit(1))
    if row is None:
        return save_profile(db, load_profile_file())
    return CandidateProfileIn.model_validate(row.profile_json)


def save_profile(db: Session, profile: CandidateProfileIn) -> CandidateProfileIn:
    row = db.scalar(select(CandidateProfile).limit(1))
    if row is None:
        row = CandidateProfile(profile_json=profile.model_dump(mode="json"))
        db.add(row)
    else:
        row.profile_json = profile.model_dump(mode="json")
    db.commit()
    return profile


def get_profile_row(db: Session) -> CandidateProfile | None:
    return db.scalar(select(CandidateProfile).limit(1))
