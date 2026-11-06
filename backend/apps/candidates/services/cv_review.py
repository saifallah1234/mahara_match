# Placement: backend/apps/candidates/services/cv_review.py
"""ATS analysis workflow: ownership, file loading and persistence around the AI capability.

The capability (ai/document_intelligence) is pure; this service is the only ORM writer.
The candidate profile is never changed here.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from ai.document_intelligence.ats.analysis import CVReviewError, analyze_cv
from ai.document_intelligence.ats.profiles import RoleProfile, roles
from ai.document_intelligence.ats.rewrite import propose_summary, rewrite_bullet
from ai.llm.providers.embeddings import embed
from ai.llm.providers.ollama import get_chat_model
from backend.apps.candidates.models import CV, CVAnalysisResult
from backend.apps.candidates.services.records import (
    get_cv_analysis,
    get_record,
    list_cv_analyses,
    require_candidate,
)
from backend.apps.documents.services.documents import download_document
from backend.apps.identity.models import User
from backend.common.exceptions import DomainValidationError

EXTRACTION_TIMEOUT_SECONDS = 30  # per section call; a timeout degrades instead of blocking
REWRITE_TIMEOUT_SECONDS = 30
EMBED_TIMEOUT_SECONDS = 10


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


def request_rewrite(actor: User, analysis_id: UUID | str, bullet_key: str) -> dict[str, Any]:
    """Validated rewrite or rule-based suggestion for one bullet; nothing is stored."""
    analysis = get_cv_analysis(actor, analysis_id)
    return rewrite_bullet(
        _bullet(analysis, bullet_key),
        _role(analysis),
        get_chat_model(timeout=REWRITE_TIMEOUT_SECONDS),
        embed=lambda texts: embed(texts, timeout=EMBED_TIMEOUT_SECONDS, attempts=1),
    )


def request_summary(actor: User, analysis_id: UUID | str) -> dict[str, Any]:
    analysis = get_cv_analysis(actor, analysis_id)
    return propose_summary(
        _structure(analysis), _role(analysis), get_chat_model(timeout=REWRITE_TIMEOUT_SECONDS)
    )


def update_draft(actor: User, analysis_id: UUID | str, change: dict[str, Any]) -> CVAnalysisResult:
    """Apply one candidate choice to the CV draft. The candidate profile is never touched.

    `change` holds exactly one of: bullet + decision (+ text), skill + has_experience, summary.
    """
    get_cv_analysis(actor, analysis_id)  # ownership check before locking
    with transaction.atomic():
        analysis = list_cv_analyses(actor).select_for_update().get(id=analysis_id)
        draft = {
            "bullets": {},
            "confirmed_skills": [],
            "declined_skills": [],
            "summary": None,
            **analysis.cv_draft_json,
        }
        if "bullet" in change:
            original = _bullet(analysis, change["bullet"])
            accepted = change["decision"] == "accept"
            text = change.get("text") or ""
            if accepted and not text:
                raise DomainValidationError("An accepted rewrite needs its text.")
            draft["bullets"][change["bullet"]] = {
                "original": original,
                "decision": change["decision"],
                "text": text if accepted else original,
            }
        elif "skill" in change:
            skill = change["skill"]
            if skill not in _missing_core_skills(analysis):
                raise DomainValidationError(f"{skill!r} is not a missing core skill.")
            yes, no = draft["confirmed_skills"], draft["declined_skills"]
            for answers in (yes, no):
                if skill in answers:
                    answers.remove(skill)
            (yes if change["has_experience"] else no).append(skill)
        else:
            draft["summary"] = change["summary"] or None
        analysis.cv_draft_json = draft
        analysis.save(update_fields=["cv_draft_json", "updated_at"])
    return analysis


def _role(analysis: CVAnalysisResult) -> RoleProfile:
    role = roles().get(analysis.role_profile_id)
    if role is None:
        raise DomainValidationError("This analysis has no role profile.")
    return role


def _structure(analysis: CVAnalysisResult) -> dict[str, Any]:
    structure = analysis.breakdown_json.get("structure")
    if not structure:
        raise DomainValidationError("This analysis has no readable CV structure.")
    return dict(structure)


def _bullet(analysis: CVAnalysisResult, key: str) -> str:
    """Key "<section>.<entry>.<bullet>", e.g. "experience.0.2", into the analysis structure."""
    section, _, rest = key.partition(".")
    entry, _, index = rest.partition(".")
    entries = _structure(analysis)["entries"]
    if section in ("experience", "projects") and entry.isdigit() and index.isdigit():
        try:
            return str(entries.get(section, [])[int(entry)]["bullets"][int(index)])
        except (IndexError, KeyError, TypeError):
            pass
    raise DomainValidationError(f"Unknown bullet {key!r}.")


def _missing_core_skills(analysis: CVAnalysisResult) -> list[str]:
    return [
        row["name"]
        for row in analysis.breakdown_json.get("skills", [])
        if row["tier"] == "core" and not row["evidence"]
    ]
