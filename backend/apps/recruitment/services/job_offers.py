from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet

from backend.apps.identity.models import Organization, RoleCode, User, UserRole
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import ORGANIZATION_ROLE_TYPES
from backend.apps.recruitment.models import JobOffer, JobOfferStatus
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.apps.recruitment.services.scope import organization_ids_with_permission
from backend.common.exceptions import (
    DomainNotFoundError,
    DomainPermissionError,
    DomainValidationError,
)

# Status, publication dates, source, external_id and created_by are lifecycle/import fields.
_EDITABLE_FIELDS = (
    "title",
    "description",
    "contract_type",
    "work_mode",
    "experience_level",
    "country_code",
    "governorate",
    "city",
    "min_salary",
    "max_salary",
    "application_deadline",
    "offer_url",
    "description_language_id",
    "education_level_id",
    "easy_apply",
)
_REFERENCE_FIELDS = ("description_language_id", "education_level_id")


def _validate_offer_fields(fields: Mapping[str, Any], offer: JobOffer | None = None) -> None:
    minimum = fields.get("min_salary", offer.min_salary if offer else None)
    maximum = fields.get("max_salary", offer.max_salary if offer else None)
    if minimum is not None and maximum is not None and maximum < minimum:
        raise DomainValidationError(details={"max_salary": ["Must be at least min_salary."]})
    if (minimum is not None and minimum < 0) or (maximum is not None and maximum < 0):
        raise DomainValidationError(details={"salary": ["Salary must be nonnegative."]})
    url = fields.get("offer_url")
    if url and not str(url).lower().startswith("https://"):
        raise DomainValidationError(details={"offer_url": ["Use an HTTPS URL."]})
    if (
        offer
        and fields.get("easy_apply", offer.easy_apply) is False
        and offer.applications.exists()
    ):
        raise DomainValidationError(
            details={"easy_apply": ["An offer with applications must stay internal."]}
        )
    if offer and offer.status == JobOfferStatus.PUBLISHED:
        if not fields.get("easy_apply", offer.easy_apply) and not fields.get(
            "offer_url", offer.offer_url
        ):
            raise DomainValidationError(
                details={"offer_url": ["External applications need a link."]}
            )
        if (
            not str(fields.get("title", offer.title)).strip()
            or not str(fields.get("description", offer.description)).strip()
        ):
            raise DomainValidationError(
                details={"offer": ["Published offers need a title and description."]}
            )


def _validate_references(fields: Mapping[str, Any]) -> None:
    errors: dict[str, list[str]] = {}
    for field in _REFERENCE_FIELDS:
        value = fields.get(field)
        if value is None:
            continue
        related_model = cast(Any, JobOffer._meta.get_field(field.removesuffix("_id"))).related_model
        if not related_model.objects.filter(pk=value).exists():
            errors[field] = ["Referenced object not found."]
    if errors:
        raise DomainValidationError(details=errors)


def _get_recruiting_organization(organization_id: UUID) -> Organization:
    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist as exc:
        raise DomainValidationError(
            details={"organization_id": ["Organization not found."]}
        ) from exc
    if organization.type not in ORGANIZATION_ROLE_TYPES[RoleCode.RECRUITER]:
        raise DomainValidationError(
            details={"organization_id": ["Only companies and subsidiaries can publish offers."]}
        )
    return organization


def list_job_offers(actor: User) -> QuerySet[JobOffer]:
    queryset = JobOffer.objects.filter(
        deleted_at__isnull=True, organization__deleted_at__isnull=True
    )
    scope = organization_ids_with_permission(actor, RecruitmentPermissionCode.READ_OFFERS)
    if scope is None:
        return queryset.order_by("created_at", "id")
    candidate = (
        actor.is_active
        and UserRole.objects.filter(user=actor, role__code=RoleCode.CANDIDATE).exists()
    )
    if not candidate and not scope:
        raise DomainPermissionError()
    visibility = Q(organization_id__in=scope)
    if candidate:
        visibility |= Q(status="PUBLISHED", organization__verification_status="VERIFIED")
    queryset = queryset.filter(visibility)
    return queryset.order_by("created_at", "id")


def get_job_offer(actor: User, offer_id: UUID | str) -> JobOffer:
    try:
        offer = list_job_offers(actor).get(id=offer_id)
    except JobOffer.DoesNotExist as exc:
        raise DomainNotFoundError("Job offer not found.") from exc
    return offer


@transaction.atomic
def create_job_offer(actor: User, data: Mapping[str, Any]) -> JobOffer:
    organization_id = data["organization_id"]
    require_permission(actor, RecruitmentPermissionCode.MANAGE_OFFERS, organization_id)
    organization = _get_recruiting_organization(organization_id)

    fields = {field: data[field] for field in _EDITABLE_FIELDS if field in data}
    _validate_offer_fields(fields)
    _validate_references(fields)
    try:
        offer = JobOffer(
            organization_id=organization.id,
            created_by=actor,
            **fields,
        )
        offer.full_clean()
        offer.save()
        return offer
    except ValidationError as exc:
        raise DomainValidationError(details=exc.message_dict) from exc
    except IntegrityError as exc:
        raise DomainValidationError(
            details={"offer": ["The offer violates a data constraint."]}
        ) from exc


@transaction.atomic
def update_job_offer(actor: User, offer: JobOffer, data: Mapping[str, Any]) -> JobOffer:
    try:
        offer = JobOffer.objects.select_for_update().get(pk=offer.pk, deleted_at__isnull=True)
    except JobOffer.DoesNotExist as exc:
        raise DomainNotFoundError("Job offer not found.") from exc
    require_permission(actor, RecruitmentPermissionCode.MANAGE_OFFERS, offer.organization_id)
    fields = {field: data[field] for field in _EDITABLE_FIELDS if field in data}
    _validate_offer_fields(fields, offer)
    _validate_references(fields)
    if not fields:
        return offer
    for field, value in fields.items():
        setattr(offer, field, value)
    try:
        offer.full_clean()
        offer.save(update_fields=[*fields, "updated_at"])
    except ValidationError as exc:
        raise DomainValidationError(details=exc.message_dict) from exc
    return offer
