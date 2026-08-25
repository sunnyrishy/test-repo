"""Strict schema for AI verification output.

LLM output is never trusted: it is parsed into these models, and anything that
fails validation is retried and then recorded as a verification error rather
than written to the jobs tables.
"""
from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Decision(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    ERROR = "ERROR"


class WorkAuthorizationStatus(StrEnum):
    CLEARLY_COMPATIBLE = "CLEARLY_COMPATIBLE"
    PROBABLY_COMPATIBLE = "PROBABLY_COMPATIBLE"
    UNKNOWN = "UNKNOWN"
    PROBABLY_INCOMPATIBLE = "PROBABLY_INCOMPATIBLE"
    CLEARLY_INCOMPATIBLE = "CLEARLY_INCOMPATIBLE"


class SponsorshipStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    POSSIBLY_AVAILABLE = "POSSIBLY_AVAILABLE"
    NOT_SPECIFIED = "NOT_SPECIFIED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    REQUIRES_CITIZENSHIP = "REQUIRES_CITIZENSHIP"


class RequirementType(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice-to-have"
    NOT_SPECIFIED = "not-specified"


class Checks(BaseModel):
    """Hard requirements. None means "could not be determined"."""

    model_config = ConfigDict(extra="forbid")

    role_match: bool | None = None
    entry_level: bool | None = None
    experience_match: bool | None = None
    degree_match: bool | None = None
    graduation_match: bool | None = None
    location_match: bool | None = None
    employment_match: bool | None = None
    citizenship_required: bool | None = None
    security_clearance_required: bool | None = None

    # Checks that must be true to pass; the two below are inverted.
    POSITIVE: ClassVar[tuple[str, ...]] = (
        "role_match",
        "entry_level",
        "experience_match",
        "degree_match",
        "location_match",
        "employment_match",
    )
    NEGATIVE: ClassVar[tuple[str, ...]] = ("citizenship_required", "security_clearance_required")

    def failures(self) -> list[str]:
        failed = [name for name in self.POSITIVE if getattr(self, name) is False]
        failed += [name for name in self.NEGATIVE if getattr(self, name) is True]
        return failed

    def unknowns(self) -> list[str]:
        return [
            name
            for name in (*self.POSITIVE, *self.NEGATIVE)
            if getattr(self, name) is None
        ]


class ExperienceFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_years: int | None = Field(default=None, ge=0, le=60)
    maximum_years: int | None = Field(default=None, ge=0, le=60)
    requirement_type: RequirementType = RequirementType.NOT_SPECIFIED


class EducationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: str | None = None
    candidate_qualifies: bool | None = None


class GraduationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explicit_year_requirement: bool | None = None
    candidate_qualifies: bool | None = None


class WorkAuthorizationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: WorkAuthorizationStatus = WorkAuthorizationStatus.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SponsorshipFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SponsorshipStatus = SponsorshipStatus.NOT_SPECIFIED


class VerificationResult(BaseModel):
    """Exactly what the model is allowed to return."""

    model_config = ConfigDict(extra="forbid")

    decision: Decision
    confidence: float = Field(ge=0.0, le=1.0)
    checks: Checks
    experience: ExperienceFinding = Field(default_factory=ExperienceFinding)
    education: EducationFinding = Field(default_factory=EducationFinding)
    graduation: GraduationFinding = Field(default_factory=GraduationFinding)
    work_authorization: WorkAuthorizationFinding = Field(
        default_factory=WorkAuthorizationFinding
    )
    sponsorship: SponsorshipFinding = Field(default_factory=SponsorshipFinding)
    matched_skills: list[str] = Field(default_factory=list, max_length=50)
    missing_skills: list[str] = Field(default_factory=list, max_length=50)
    rejection_reasons: list[str] = Field(default_factory=list, max_length=20)
    summary: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def enforce_decision_logic(self) -> "VerificationResult":
        """The decision must follow from the checks, not from model vibes.

        A model that calls every hard check true but still says FAIL - or
        worse, reports a failed check and says PASS - has its decision
        corrected here, because the checks are the evidence.
        """
        if self.decision is Decision.ERROR:
            return self
        failures = self.checks.failures()
        unknowns = self.checks.unknowns()
        if failures:
            derived = Decision.FAIL
        elif unknowns:
            derived = Decision.REVIEW
        else:
            derived = Decision.PASS
        if derived is not self.decision:
            self.decision = derived
            reason = f"decision corrected to {derived.value} from checks"
            if reason not in self.rejection_reasons:
                self.rejection_reasons.append(reason)
        if self.decision is Decision.FAIL and not self.rejection_reasons:
            self.rejection_reasons = [f"failed checks: {', '.join(failures)}"]
        return self


class VerificationOut(BaseModel):
    """Verification as exposed on the API."""

    model_config = ConfigDict(from_attributes=True)

    decision: str
    confidence: float
    role_match: bool | None
    entry_level: bool | None
    experience_match: bool | None
    degree_match: bool | None
    graduation_match: bool | None
    location_match: bool | None
    employment_match: bool | None
    citizenship_required: bool | None
    security_clearance_required: bool | None
    experience_required: int | None
    experience_type: str | None
    education_required: str | None
    work_authorization_status: str
    sponsorship_status: str
    matched_skills: list[str]
    missing_skills: list[str]
    rejection_reasons: list[str]
    ai_summary: str | None
    model: str | None
