import pytest
from django.test import override_settings

from backend.apps.assistant.services.interview_contracts import (
    AVATARS,
    InterviewConflict,
    fingerprint,
    validate_key,
    validate_language,
    validate_transition,
)
from backend.common.exceptions import DomainValidationError


@override_settings(MOCK_INTERVIEW_LANGUAGES=("fr",))
def test_language_contract():
    validate_language("fr")
    for language in ("en", "ar-TN", "de", ""):
        with pytest.raises(DomainValidationError):
            validate_language(language)


def test_state_and_key_contracts():
    validate_transition("PREPARING", "READY")
    for current, target in (
        ("PREPARING", "COMPLETED"),
        ("COMPLETED", "IN_PROGRESS"),
        ("READY", "THINKING"),
    ):
        with pytest.raises(InterviewConflict):
            validate_transition(current, target)
    for key in ("", "a" * 256, "line\nbreak"):
        with pytest.raises(DomainValidationError):
            validate_key(key)
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})
    assert AVATARS["followup"] == "avatars/followup.mp4"
