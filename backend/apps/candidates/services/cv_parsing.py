# Placement: backend/apps/candidates/services/cv_parsing.py
"""CV analysis: start it, store the raw result, propose profile entries, apply them.

Flow (CONTEXT.md, G05):
1. request_cv_parsing: the candidate asks to analyse one of their CVs. The CV goes
   to PROCESSING and `python -m pipelines.document_processing.cv_parsing --cv-id`
   starts in the background (an LLM pass takes from seconds to ~10 minutes).
2. The pipeline reads the file (cv_file_for_parsing), extracts, and stores the raw
   result on the CV (store_cv_parse_result) -> PARSED, or FAILED.
3. cv_profile_proposal: the proposal with references resolved (existing skill,
   language and education level ids) for the review screen.
4. apply_cv_proposal: only what the candidate confirmed is written, in one
   transaction, through the normal record rules. Raw results stay on the CV,
   separate from the validated profile.
"""

from collections.abc import Mapping
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from backend.apps.candidates.models import (
    CV,
    CandidateLanguage,
    CandidateSkill,
    Certification,
    Education,
    Experience,
    Project,
)
from backend.apps.candidates.services import records
from backend.apps.documents.services.documents import download_document
from backend.apps.identity.models import User
from backend.apps.taxonomy.models import EducationLevel, Language
from backend.apps.taxonomy.services.education import level_for_degree
from backend.apps.taxonomy.services.skills import find_skill, get_or_create_skill
from backend.common import background
from backend.common.exceptions import DomainNotFoundError, DomainValidationError
from backend.common.exceptions.domain import DomainError

PIPELINE_MODULE = "pipelines.document_processing.cv_parsing"
PROCESSING = "PROCESSING"
PARSED = "PARSED"
FAILED = "FAILED"
STALE_AFTER = timedelta(minutes=30)  # a run never takes this long; a dead one unblocks
SKILL_SOURCE = "CV"


class CVParsingAlreadyRunning(DomainError):
    code = "cv_parsing_running"
    status_code = 409
    default_message = "This CV is already being analysed."


class CVParsingLaunchFailed(DomainError):
    code = "cv_parsing_launch_failed"
    status_code = 503
    default_message = "The CV analysis could not be started."


# -- 1. start ------------------------------------------------------------------------


def request_cv_parsing(actor: User, cv_id: UUID | str) -> CV:
    with transaction.atomic():
        cv = records.get_record(actor, CV, cv_id)
        cv = CV.objects.select_for_update().get(pk=cv.pk)
        if cv.bytes_purged_at is not None:
            raise DomainValidationError(details={"cv": ["The file of this CV was deleted."]})
        if cv.parse_status == PROCESSING and cv.updated_at > timezone.now() - STALE_AFTER:
            raise CVParsingAlreadyRunning()
        cv.parse_status = PROCESSING
        cv.parsed_data_json = None
        cv.save(update_fields=["parse_status", "parsed_data_json", "updated_at"])
    try:
        _spawn(cv.pk)
    except OSError as exc:
        mark_cv_parse_failed(cv.pk, "The analysis process could not be started.")
        raise CVParsingLaunchFailed() from exc
    return cv


def _spawn(cv_id: UUID) -> None:
    background.start_module(
        PIPELINE_MODULE, ["--cv-id", str(cv_id)], background.logs_dir("cv") / f"{cv_id}.log"
    )


# -- 2. pipeline side (system, no actor) ---------------------------------------------


def cv_file_for_parsing(cv_id: UUID | str) -> tuple[bytes, str]:
    """The CV file and its MIME type, for the analysis process."""
    cv = CV.objects.select_related("document").filter(pk=cv_id, deleted_at__isnull=True).first()
    if cv is None:
        raise DomainNotFoundError("CV not found.")
    document, content = download_document(cv.document)
    return content, document.mime_type


def store_cv_parse_result(
    cv_id: UUID | str, *, extraction: Mapping[str, Any], proposal: Mapping[str, Any], provider: str
) -> None:
    CV.objects.filter(pk=cv_id).update(
        parse_status=PARSED,
        parsed_data_json={
            "extraction": dict(extraction),
            "proposal": dict(proposal),
            "provider": provider,
            "parsed_at": timezone.now().isoformat(),
        },
        updated_at=timezone.now(),
    )


def mark_cv_parse_failed(cv_id: UUID | str, reason: str) -> None:
    CV.objects.filter(pk=cv_id).update(
        parse_status=FAILED,
        parsed_data_json={"error": reason[:500]},
        updated_at=timezone.now(),
    )


# -- 3. review -----------------------------------------------------------------------


def cv_profile_proposal(actor: User, cv_id: UUID | str) -> dict[str, Any]:
    cv = records.get_record(actor, CV, cv_id)
    data = cv.parsed_data_json or {}
    if cv.parse_status != PARSED or "proposal" not in data:
        raise DomainValidationError(details={"cv": ["This CV has not been analysed yet."]})
    proposal: dict[str, Any] = dict(data["proposal"])
    profile = records.own_profile(actor)

    own_skills = set(
        CandidateSkill.objects.filter(candidate=profile).values_list("skill_id", flat=True)
    )
    skills = []
    for item in proposal.get("skills", []):
        skill = find_skill(item["name"])
        skills.append(
            {
                **item,
                "skill_id": str(skill.pk) if skill else None,
                "name": skill.canonical_name if skill else item["name"],
                "already_on_profile": bool(skill and skill.pk in own_skills),
            }
        )

    own_languages = set(
        CandidateLanguage.objects.filter(candidate=profile).values_list("language__code", flat=True)
    )
    language_ids = {code: str(pk) for pk, code in Language.objects.values_list("pk", "code")}
    languages = [
        {
            **item,
            "language_id": language_ids.get(item.get("code") or ""),
            "already_on_profile": (item.get("code") or "") in own_languages,
        }
        for item in proposal.get("languages", [])
    ]

    # Entries already on the profile come unticked, so a second "Ajouter" adds no duplicates.
    own_experiences = {
        (_key(title), _key(org), str(start))
        for title, org, start in Experience.objects.filter(candidate=profile).values_list(
            "job_title", "organization_name", "start_date"
        )
    }
    experiences = [
        {
            **item,
            "already_on_profile": (
                _key(item.get("job_title")),
                _key(item.get("organization_name")),
                str(item.get("start_date")),
            )
            in own_experiences,
        }
        for item in proposal.get("experiences", [])
    ]
    own_educations = {
        (_key(institution), year)
        for institution, year in Education.objects.filter(candidate=profile).values_list(
            "institution", "start_year"
        )
    }
    educations = []
    for item in proposal.get("educations", []):
        level = level_for_degree(item.get("degree_level"))
        educations.append(
            {
                **item,
                "education_level": str(level.pk) if level else None,
                "already_on_profile": (_key(item.get("institution")), item.get("start_year"))
                in own_educations,
            }
        )
    own_certifications = {
        _key(name)
        for name in Certification.objects.filter(candidate=profile).values_list("name", flat=True)
    }
    certifications = [
        {**item, "already_on_profile": _key(item.get("name")) in own_certifications}
        for item in proposal.get("certifications", [])
    ]
    own_projects = {
        _key(name)
        for name in Project.objects.filter(candidate=profile).values_list("name", flat=True)
    }
    projects = [
        {**item, "already_on_profile": _key(item.get("name")) in own_projects}
        for item in proposal.get("projects", [])
    ]

    return {
        "cv_id": str(cv.pk),
        "provider": data.get("provider", ""),
        "parsed_at": data.get("parsed_at"),
        "identity": proposal.get("identity", {}),
        "experiences": experiences,
        "educations": educations,
        "skills": skills,
        "languages": languages,
        "certifications": certifications,
        "projects": projects,
    }


def _key(text: Any) -> str:
    return " ".join(str(text or "").casefold().split())


# -- 4. apply what the candidate confirmed -----------------------------------------------


@transaction.atomic
def apply_cv_proposal(actor: User, cv_id: UUID | str, data: Mapping[str, Any]) -> dict[str, int]:
    """Create the confirmed entries. All or nothing; errors name the section and row."""
    cv = records.get_record(actor, CV, cv_id)
    if cv.parse_status != PARSED:
        raise DomainValidationError(details={"cv": ["This CV has not been analysed yet."]})
    profile = records.own_profile(actor)
    counts = {
        kind: 0
        for kind in (
            "experiences",
            "educations",
            "skills",
            "languages",
            "certifications",
            "projects",
        )
    }

    def create(kind: str, index: int, model: Any, values: dict[str, Any]) -> None:
        try:
            records.create_record(actor, model, values)
        except DomainValidationError as exc:
            raise DomainValidationError(
                f"{kind} #{index + 1}: {exc.message}", details={kind: {index: exc.details}}
            ) from exc
        counts[kind] += 1

    for index, item in enumerate(data.get("experiences", [])):
        create("experiences", index, Experience, dict(item))
    for index, item in enumerate(data.get("educations", [])):
        values = dict(item)
        level = EducationLevel.objects.filter(pk=values.pop("education_level", None)).first()
        if level is None:
            raise DomainValidationError(
                details={"educations": {index: {"education_level": ["Choose a level."]}}}
            )
        create("educations", index, Education, {**values, "education_level": level})
    for index, item in enumerate(data.get("certifications", [])):
        create("certifications", index, Certification, dict(item))

    own_skills = set(
        CandidateSkill.objects.filter(candidate=profile).values_list("skill_id", flat=True)
    )
    for index, item in enumerate(data.get("skills", [])):
        skill = get_or_create_skill(item["name"], item.get("category", ""))
        if skill.pk in own_skills:
            continue  # already on the profile; never duplicated or overwritten
        own_skills.add(skill.pk)
        create(
            "skills",
            index,
            CandidateSkill,
            {"skill": skill, "level": item["level"], "source": SKILL_SOURCE, "validated": False},
        )

    own_languages = set(
        CandidateLanguage.objects.filter(candidate=profile).values_list("language_id", flat=True)
    )
    for index, item in enumerate(data.get("languages", [])):
        language = Language.objects.filter(pk=item["language_id"]).first()
        if language is None:
            raise DomainValidationError(
                details={"languages": {index: {"language_id": ["Unknown language."]}}}
            )
        if language.pk in own_languages:
            continue
        own_languages.add(language.pk)
        create(
            "languages", index, CandidateLanguage, {"language": language, "level": item["level"]}
        )

    for index, item in enumerate(data.get("projects", [])):
        values = dict(item)
        names = values.pop("technologies", [])
        technologies = list(
            {skill.pk: skill for skill in (get_or_create_skill(n) for n in names)}.values()
        )
        create("projects", index, Project, {**values, "technologies": technologies})
    return counts
