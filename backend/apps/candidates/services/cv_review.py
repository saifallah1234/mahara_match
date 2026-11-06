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
from backend.apps.candidates.models import CV, CVAnalysisResult
from backend.apps.candidates.services.records import get_record, require_candidate
from backend.apps.documents.services.documents import download_document
from backend.apps.identity.models import User
from backend.common.exceptions import DomainValidationError


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
    try:
        result = analyze_cv(content, role_profile_id, level)
    except CVReviewError as exc:
        raise DomainValidationError(str(exc)) from exc
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
