from datetime import datetime

from pydantic import BaseModel, Field


class Degree(BaseModel):
    level: str
    field: str
    accepted_levels: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    maximum_preferred_years: int = 1


class CandidateProfileIn(BaseModel):
    """Validated shape of the configurable candidate profile."""

    graduation_year: int
    degree: Degree
    country: str = "US"
    employment_types: list[str] = Field(default_factory=lambda: ["FullTime"])
    experience: Experience = Field(default_factory=Experience)
    career_stage: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    related_roles: list[str] = Field(default_factory=list)
    excluded_roles: list[str] = Field(default_factory=list)
    excluded_seniority_terms: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class CandidateProfileOut(BaseModel):
    profile: CandidateProfileIn
    updated_at: datetime | None = None
