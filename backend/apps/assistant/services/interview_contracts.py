"""Mock interview contracts shared by persistence and transport."""

import hashlib
import json
from typing import Any

from django.conf import settings

from backend.common.exceptions import DomainError, DomainValidationError
from pipelines.interviews.queue import AVATARS as AVATARS

LANGUAGES = ("fr", "en", "ar-TN")


class InterviewConflict(DomainError):
    code = "conflict"
    status_code = 409


class InterviewUnavailable(DomainError):
    code = "interview_unavailable"
    status_code = 503
    default_message = "The required interview integration is unavailable."


def validate_language(language: str) -> None:
    if language not in LANGUAGES or language not in settings.MOCK_INTERVIEW_LANGUAGES:
        raise DomainValidationError(details={"language": ["Language is disabled or unsupported."]})


def validate_key(key: str) -> None:
    if not key or len(key) > 255 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise DomainValidationError(
            details={"idempotency_key": ["Use 1–255 visible ASCII characters."]}
        )


def fingerprint(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


SESSION_TRANSITIONS = {
    "PREPARING": {"READY", "FAILED", "CANCELLED"},
    "READY": {"IN_PROGRESS", "FAILED", "CANCELLED"},
    "IN_PROGRESS": {"THINKING", "FAILED", "CANCELLED"},
    "THINKING": {"IN_PROGRESS", "EVALUATING", "FAILED", "CANCELLED"},
    "EVALUATING": {"COMPLETED", "FAILED", "CANCELLED"},
    "FAILED": {"PREPARING", "THINKING", "EVALUATING", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}


def validate_transition(current: str, target: str) -> None:
    if target not in SESSION_TRANSITIONS.get(current, set()):
        raise InterviewConflict("Invalid interview transition.")
