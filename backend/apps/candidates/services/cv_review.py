# Placement: backend/apps/candidates/services/cv_review.py
"""ATS analysis workflow: ownership, file loading and persistence around the AI capability.

The capability (ai/document_intelligence) is pure; this service is the only ORM writer.
The candidate profile is never changed here.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone

from ai.document_intelligence.ats.analysis import CVReviewError, analyze_cv
from ai.document_intelligence.ats.profiles import RoleProfile, levels, roles
from ai.document_intelligence.ats.rewrite import propose_summary, rewrite_bullet
from ai.document_intelligence.generation.cv_writer import GeneratedCV, generate_cv
from ai.llm.providers.embeddings import embed
from ai.llm.providers.ollama import get_chat_model
from backend.apps.candidates.models import CV, CVAnalysisResult
from backend.apps.candidates.services.records import (
    create_cv,
    get_cv_analysis,
    get_record,
    list_cv_analyses,
    require_candidate,
)
from backend.apps.documents.services.documents import download_document, upload_document
from backend.apps.identity.models import User
from backend.common.exceptions import DomainValidationError

EXTRACTION_TIMEOUT_SECONDS = 30  # per section call; a timeout degrades instead of blocking
REWRITE_TIMEOUT_SECONDS = 30
EMBED_TIMEOUT_SECONDS = 10
MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


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


def generate_file(
    actor: User, analysis_id: UUID | str, file_format: str
) -> tuple[GeneratedCV, str]:
    """The CV draft as an ATS-friendly file and its download name; nothing is stored."""
    return _generate(get_cv_analysis(actor, analysis_id), file_format)


def save_as_cv(actor: User, analysis_id: UUID | str, file_format: str) -> CV:
    """Store the generated file as a new CV version (next number, not primary). Needs the
    candidate's explicit confirmation in the UI; the candidate profile is not changed."""
    analysis = get_cv_analysis(actor, analysis_id)
    generated, file_name = _generate(analysis, file_format)
    upload = SimpleUploadedFile(file_name, generated.content, MIME_TYPES[file_format])
    with transaction.atomic():
        document = upload_document(actor, upload, "CV")
        return create_cv(
            actor,
            {
                "document": document,
                "title": f"ATS {_role(analysis).label} (depuis v{analysis.cv.version_number})",
                "language_code": "en",
            },
        )


def _generate(analysis: CVAnalysisResult, file_format: str) -> tuple[GeneratedCV, str]:
    cv, role = analysis.cv, _role(analysis)
    level = levels().get(analysis.level)
    if level is None or file_format not in MIME_TYPES:
        raise DomainValidationError("This analysis cannot be generated in that format.")
    if cv.bytes_purged_at is not None:
        raise DomainValidationError("This CV file is no longer available.")
    _, content = download_document(cv.document)
    try:
        generated = generate_cv(content, analysis.cv_draft_json, role, level, file_format)
    except ValueError as exc:
        raise DomainValidationError(str(exc)) from exc
    return generated, f"cv-{role.id.replace('_', '-')}-v{cv.version_number}.{file_format}"


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


_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
CV_ADVICE_POINTS = 4


def latest_cv_advice(actor: User) -> dict[str, Any]:
    """Assistant evidence: the top issues of the candidate's latest ATS analysis, read-only."""
    analysis = list_cv_analyses(actor).select_related("cv").first()
    if analysis is None:
        return {"reason": "no_cv_analysis", "matches": []}
    role = roles().get(analysis.role_profile_id)
    issues = sorted(
        analysis.issues_json, key=lambda issue: _SEVERITY_ORDER.get(issue.get("severity"), 3)
    )
    return {
        "reason": "analysis_found",
        "matches": [],
        "analysis_id": str(analysis.id),
        "cv_title": analysis.cv.title,
        "cv_version": analysis.cv.version_number,
        "role": role.label if role else analysis.role_profile_id,
        "score": round(analysis.overall_score),
        "points": [issue["message"] for issue in issues[:CV_ADVICE_POINTS]],
    }
