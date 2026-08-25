"""AI output validation: malformed or self-contradictory output never lands."""
import json

import pytest
from pydantic import ValidationError

from app.schemas.verification import Decision, VerificationResult
from app.services.verification import parse_result

PASSING = {
    "decision": "PASS",
    "confidence": 0.94,
    "checks": {
        "role_match": True,
        "entry_level": True,
        "experience_match": True,
        "degree_match": True,
        "graduation_match": True,
        "location_match": True,
        "employment_match": True,
        "citizenship_required": False,
        "security_clearance_required": False,
    },
    "summary": "Entry-level software role suitable for a 2026 MSCS graduate.",
}


def test_valid_payload_parses():
    result = parse_result(json.dumps(PASSING))
    assert result.decision is Decision.PASS
    assert result.confidence == 0.94


def test_json_wrapped_in_code_fence_is_accepted():
    assert parse_result(f"```json\n{json.dumps(PASSING)}\n```").decision is Decision.PASS


def test_prose_around_json_is_tolerated():
    raw = f"Here is my answer:\n{json.dumps(PASSING)}\nHope that helps."
    assert parse_result(raw).decision is Decision.PASS


def test_output_without_json_is_rejected():
    with pytest.raises(ValueError):
        parse_result("I think this job looks like a good fit!")


def test_unknown_field_is_rejected():
    payload = {**PASSING, "vibes": "great"}
    with pytest.raises(ValidationError):
        parse_result(json.dumps(payload))


def test_out_of_range_confidence_is_rejected():
    with pytest.raises(ValidationError):
        parse_result(json.dumps({**PASSING, "confidence": 1.5}))


def test_invalid_enum_is_rejected():
    payload = {**PASSING, "work_authorization": {"status": "MAYBE", "confidence": 0.5}}
    with pytest.raises(ValidationError):
        parse_result(json.dumps(payload))


def test_missing_decision_is_rejected():
    payload = {k: v for k, v in PASSING.items() if k != "decision"}
    with pytest.raises(ValidationError):
        parse_result(json.dumps(payload))


# --- decision must follow from the checks ---

def test_pass_is_downgraded_when_a_hard_check_failed():
    payload = {**PASSING, "checks": {**PASSING["checks"], "experience_match": False}}
    result = parse_result(json.dumps(payload))
    assert result.decision is Decision.FAIL
    assert result.rejection_reasons


def test_pass_is_downgraded_when_citizenship_is_required():
    payload = {**PASSING, "checks": {**PASSING["checks"], "citizenship_required": True}}
    assert parse_result(json.dumps(payload)).decision is Decision.FAIL


def test_pass_is_downgraded_when_clearance_is_required():
    payload = {
        **PASSING,
        "checks": {**PASSING["checks"], "security_clearance_required": True},
    }
    assert parse_result(json.dumps(payload)).decision is Decision.FAIL


def test_unknown_check_becomes_review():
    payload = {**PASSING, "checks": {**PASSING["checks"], "degree_match": None}}
    assert parse_result(json.dumps(payload)).decision is Decision.REVIEW


def test_unjustified_fail_is_corrected_to_pass():
    # Every hard check is satisfied, so FAIL is not the model's call to make.
    payload = {**PASSING, "decision": "FAIL"}
    assert parse_result(json.dumps(payload)).decision is Decision.PASS


def test_fail_always_carries_a_reason():
    payload = {**PASSING, "checks": {**PASSING["checks"], "role_match": False}}
    assert parse_result(json.dumps(payload)).rejection_reasons


def test_error_decision_is_left_alone():
    result = VerificationResult(
        decision=Decision.ERROR, confidence=0.0, checks={}, rejection_reasons=["boom"]
    )
    assert result.decision is Decision.ERROR
