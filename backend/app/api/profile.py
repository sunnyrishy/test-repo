from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import require_admin
from app.schemas.candidate import CandidateProfileIn, CandidateProfileOut
from app.services import profile as profile_service

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=CandidateProfileOut)
def read_profile(db: Session = Depends(get_db)) -> CandidateProfileOut:
    profile = profile_service.get_profile(db)
    row = profile_service.get_profile_row(db)
    return CandidateProfileOut(profile=profile, updated_at=row.updated_at if row else None)


@router.put("", response_model=CandidateProfileOut, dependencies=[Depends(require_admin)])
def update_profile(
    payload: CandidateProfileIn, db: Session = Depends(get_db)
) -> CandidateProfileOut:
    profile_service.save_profile(db, payload)
    row = profile_service.get_profile_row(db)
    return CandidateProfileOut(profile=payload, updated_at=row.updated_at if row else None)
