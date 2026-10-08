from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Max, QuerySet
from django.utils import timezone

from backend.apps.candidates.models import (
    CV,
    CandidateProfile,
    CVAnalysisResult,
    Project,
    ProjectSkill,
)
from backend.apps.documents.services.documents import DocumentStorageError, get_owned_document
from backend.apps.identity.models import RoleCode, User, UserRole
from backend.common.exceptions import (
    DomainNotFoundError,
    DomainPermissionError,
    DomainValidationError,
)
from backend.common.storage import object_storage


def require_candidate(actor: User) -> None:
    if (
        not actor.is_active
        or not UserRole.objects.filter(
            user=actor, role__code=RoleCode.CANDIDATE, organization__isnull=True
        ).exists()
    ):
        raise DomainPermissionError()


def own_profile(actor: User) -> CandidateProfile:
    require_candidate(actor)
    try:
        return CandidateProfile.objects.get(user=actor)
    except CandidateProfile.DoesNotExist as exc:
        raise DomainNotFoundError("Candidate profile not found.") from exc


def _save_validated[RecordT: models.Model](instance: RecordT) -> RecordT:
    try:
        instance.full_clean()
        instance.save()
    except ValidationError as exc:
        raise DomainValidationError(details=exc.message_dict) from exc
    except IntegrityError as exc:
        raise DomainValidationError(
            "A uniqueness or relationship constraint was violated."
        ) from exc
    return instance


def _unique_technologies(technologies: list[Any]) -> list[Any]:
    if len({skill.pk for skill in technologies}) != len(technologies):
        raise DomainValidationError(details={"technologies": ["Duplicate skill references."]})
    return technologies


@transaction.atomic
def create_profile(actor: User, data: Mapping[str, Any]) -> CandidateProfile:
    require_candidate(actor)
    if CandidateProfile.objects.filter(user=actor).exists():
        raise DomainValidationError("A candidate profile already exists.")
    return _save_validated(CandidateProfile(user=actor, **data))


@transaction.atomic
def update_profile(actor: User, data: Mapping[str, Any]) -> CandidateProfile:
    profile = own_profile(actor)
    for field, value in data.items():
        setattr(profile, field, value)
    return _save_validated(profile)


def list_records[RecordT: models.Model](actor: User, model: type[RecordT]) -> QuerySet[RecordT]:
    profile = own_profile(actor)
    queryset = cast(Any, model).objects.filter(candidate=profile)
    if model is CV:
        queryset = queryset.filter(deleted_at__isnull=True)
    return queryset.order_by("created_at", "id")


def get_record[RecordT: models.Model](
    actor: User, model: type[RecordT], record_id: UUID | str
) -> RecordT:
    try:
        return list_records(actor, model).get(id=record_id)
    except cast(Any, model).DoesNotExist as exc:
        raise DomainNotFoundError("Record not found.") from exc


@transaction.atomic
def create_record[RecordT: models.Model](
    actor: User, model: type[RecordT], data: Mapping[str, Any]
) -> RecordT:
    profile = own_profile(actor)
    if model is CV:
        raise DomainValidationError("Use the CV version service.")
    if model is Project:
        technologies = _unique_technologies(data.get("technologies", []))
        project = _save_validated(
            Project(
                candidate=profile,
                **{key: value for key, value in data.items() if key != "technologies"},
            )
        )
        ProjectSkill.objects.bulk_create(
            [ProjectSkill(project=project, skill=skill) for skill in technologies]
        )
        return project  # type: ignore[return-value]
    return _save_validated(model(candidate=profile, **data))


@transaction.atomic
def update_record[RecordT: models.Model](
    actor: User, model: type[RecordT], record_id: UUID | str, data: Mapping[str, Any]
) -> RecordT:
    record = get_record(actor, model, record_id)
    if model is CV:
        raise DomainValidationError("Use the CV version service.")
    for field, value in data.items():
        if field != "technologies":
            setattr(record, field, value)
    _save_validated(record)
    if model is Project and "technologies" in data:
        technologies = _unique_technologies(data["technologies"])
        ProjectSkill.objects.filter(project=cast(Project, record)).delete()
        ProjectSkill.objects.bulk_create(
            [ProjectSkill(project=cast(Project, record), skill=skill) for skill in technologies]
        )
    return record


@transaction.atomic
def create_cv(actor: User, data: Mapping[str, Any]) -> CV:
    profile = own_profile(actor)
    document = get_owned_document(actor, data["document"].id)
    if CV.objects.filter(document=document).exists():
        raise DomainValidationError(details={"document": ["Document is already linked to a CV."]})
    # Serialize version allocation on the one stable row shared by all candidate CVs.
    CandidateProfile.objects.select_for_update().get(pk=profile.pk)
    next_version = (
        CV.objects.filter(candidate=profile).aggregate(maximum=Max("version_number"))["maximum"]
        or 0
    ) + 1
    primary = bool(data.get("is_primary", False))
    if primary:
        CV.objects.filter(candidate=profile, is_primary=True).update(is_primary=False)
    return _save_validated(
        CV(
            candidate=profile,
            document=document,
            title=data["title"],
            language_code=data.get("language_code", ""),
            is_primary=primary,
            version_number=next_version,
        )
    )


@transaction.atomic
def update_cv(actor: User, cv_id: UUID | str, data: Mapping[str, Any]) -> CV:
    cv = get_record(actor, CV, cv_id)
    if "document" in data and data["document"].pk != cv.document_id:
        raise DomainValidationError(
            details={"document": ["A CV version's document cannot change."]}
        )
    if data.get("is_primary") is True:
        CandidateProfile.objects.select_for_update().get(pk=cv.candidate_id)
        CV.objects.filter(candidate=cv.candidate, is_primary=True).exclude(pk=cv.pk).update(
            is_primary=False
        )
    for field, value in data.items():
        if field != "document":
            setattr(cv, field, value)
    return _save_validated(cv)


@transaction.atomic
def delete_cv(actor: User, cv_id: UUID | str) -> None:
    cv = CV.objects.select_for_update().get(pk=get_record(actor, CV, cv_id).pk)
    cv.deleted_at = timezone.now()
    cv.is_primary = False
    cv.save(update_fields=["deleted_at", "is_primary", "updated_at"])
    try:
        purge_cv_bytes(cv.id)
    except DocumentStorageError:
        pass  # The daily purge command retries storage failures.


@transaction.atomic
def purge_cv_bytes(cv_id: UUID | str) -> bool:
    from backend.apps.recruitment.models import Application, ApplicationStatus

    cv = CV.objects.select_for_update().select_related("document").get(pk=cv_id)
    if cv.deleted_at is None or cv.bytes_purged_at is not None:
        return False
    if Application.objects.filter(cv=cv).exclude(status=ApplicationStatus.REJECTED).exists():
        return False
    try:
        object_storage.delete_object(cv.document.storage_uri)
    except Exception as exc:
        raise DocumentStorageError() from exc
    cv.bytes_purged_at = timezone.now()
    cv.save(update_fields=["bytes_purged_at", "updated_at"])
    return True


def list_cv_analyses(actor: User) -> QuerySet[CVAnalysisResult]:
    profile = own_profile(actor)
    return CVAnalysisResult.objects.filter(
        cv__candidate=profile, cv__deleted_at__isnull=True
    ).order_by("-analyzed_at", "id")


def get_cv_analysis(actor: User, analysis_id: UUID | str) -> CVAnalysisResult:
    try:
        return list_cv_analyses(actor).get(id=analysis_id)
    except CVAnalysisResult.DoesNotExist as exc:
        raise DomainNotFoundError("CV analysis not found.") from exc
