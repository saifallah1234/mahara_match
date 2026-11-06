# Placement: backend/apps/candidates/services/cv_review.py
"""ATS analysis workflow: ownership, file loading and persistence around the AI capability.

The capability (ai/document_intelligence) is pure; this service is the only ORM writer.
The candidate profile is never changed here.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.utils import timezone

from ai.document_intelligence.ats.analysis import CVReviewError, analyze_cv
from ai.document_intelligence.ats.profiles import roles
from ai.llm.providers.ollama import get_chat_model
from backend.apps.candidates.models import CV, CVAnalysisResult
from backend.apps.candidates.services.records import get_record, require_candidate
from backend.apps.documents.services.documents import download_document
from backend.apps.identity.models import User
from backend.common.exceptions import DomainValidationError

EXTRACTION_TIMEOUT_SECONDS = 30  # per section call; a timeout degrades instead of blocking


def list_roles(actor: User) -> list[dict[str, Any]]:
    require_candidate(actor)
    return [
        {"id": role.id, "label": role.label, "version": role.version} for role in roles().values()
    ]


def create_analysis(
    actor: User, cv_id: UUID | str, role_profile_id: str, level: str
) -> CVAnalysisResult:
    cv = get_record(actor, CV, cv_id)  # owned and not deleted, else 404
    if cv.bytes_purged_at is not None:
        raise DomainValidationError("This CV file is no longer available.")
    _, content = download_document(cv.document)
    checksum = cv.document.checksum
    cache = cv.parsed_data_json or {}
    # A degraded parse is not reused, so the model is retried once it is back.
    cached = cache if cv.parse_status == "parsed" and cache.get("checksum") == checksum else None
    try:
        result = analyze_cv(
            content,
            role_profile_id,
            level,
            model=get_chat_model(timeout=EXTRACTION_TIMEOUT_SECONDS),
            cached=cached,
        )
    except CVReviewError as exc:
        raise DomainValidationError(str(exc)) from exc
    if result.parsed is not None and result.parsed is not cached:
        cv.parsed_data_json = {**result.parsed, "checksum": checksum}
        cv.parse_status = "degraded" if result.parsed["degraded"] else "parsed"
        cv.save(update_fields=["parsed_data_json", "parse_status", "updated_at"])
    return CVAnalysisResult.objects.create(
        cv=cv,
        overall_score=Decimal(str(result.overall_score)),
        issues_json=result.issues,
        suggestions_json=[],
        analyzed_at=timezone.now(),
        role_profile_id=result.role.id,
        role_profile_version=result.role.version,
        level=result.level.id,
        breakdown_json=result.breakdown,
        cv_draft_json={},
    )
