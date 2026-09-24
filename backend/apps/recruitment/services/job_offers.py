from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from django.apps import apps
from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from backend.apps.identity.models import RoleCode, User
from backend.apps.identity.services.access import has_permission, require_permission
from backend.apps.identity.services.contracts import ORGANIZATION_ROLE_TYPES
from backend.apps.recruitment.models import JobOffer
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.apps.recruitment.services.scope import restrict_to_organizations
from backend.common.exceptions import (
    DomainNotFoundError,
    DomainValidationError,
)

# Whitelist of caller-editable fields. Status, publication dates, source, external_id,
# created_by and salaries (Q10: no currency yet) are deliberately NOT editable here.
_EDITABLE_FIELDS = (
    "title",
    "description",
    "contract_type",
    "work_mode",
    "experience_level",
    "country_code",
    "governorate",
    "city",
    "application_deadline",
    "offer_url",
    "description_language_id",
    "required_language_id",
    "education_level_id",
    "easy_apply",
)
_REFERENCE_FIELDS = ("description_language_id", "required_language_id", "education_level_id")


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


def _get_recruiting_organization(organization_id: UUID) -> Any:
    try:
        organization_model = apps.get_model("identity", "Organization")
    except LookupError as exc:
        raise DomainValidationError(
            "Organization integration is not available until the P4 identity models are merged."
        ) from exc
    try:
        organization = organization_model.objects.get(id=organization_id)
    except organization_model.DoesNotExist as exc:
        raise DomainValidationError(
            details={"organization_id": ["Organization not found."]}
        ) from exc
    if organization.type not in ORGANIZATION_ROLE_TYPES[RoleCode.RECRUITER]:
        raise DomainValidationError(
            details={"organization_id": ["Only companies and subsidiaries can publish offers."]}
        )
    return organization


def list_job_offers(actor: User) -> QuerySet[JobOffer]:
    # TODO(G03): candidate-facing visibility (e.g. published offers only) is undecided.
    queryset = restrict_to_organizations(
        actor,
        JobOffer.objects.filter(deleted_at__isnull=True),
        RecruitmentPermissionCode.READ_OFFERS,
        "organization_id",
    )
    return queryset.order_by("created_at", "id")


def get_job_offer(actor: User, offer_id: UUID | str) -> JobOffer:
    try:
        offer = JobOffer.objects.get(id=offer_id, deleted_at__isnull=True)
    except JobOffer.DoesNotExist as exc:
        raise DomainNotFoundError("Job offer not found.") from exc
    # Unreadable offers look non-existent, so their existence is not leaked.
    if not has_permission(actor, RecruitmentPermissionCode.READ_OFFERS, offer.organization_id):
        raise DomainNotFoundError("Job offer not found.")
    return offer


@transaction.atomic
def create_job_offer(actor: User, data: Mapping[str, Any]) -> JobOffer:
    organization_id = data["organization_id"]
    require_permission(actor, RecruitmentPermissionCode.MANAGE_OFFERS, organization_id)
    organization = _get_recruiting_organization(organization_id)

    fields = {field: data[field] for field in _EDITABLE_FIELDS if field in data}
    _validate_references(fields)
    try:
        # status defaults to DRAFT; publication is a Phase 2 service (see phase_01 plan).
        return JobOffer.objects.create(
            organization_id=organization.id,
            created_by=actor,
            **fields,
        )
    except IntegrityError as exc:
        raise DomainValidationError(
            details={"offer": ["The offer violates a data constraint."]}
        ) from exc


@transaction.atomic
def update_job_offer(actor: User, offer: JobOffer, data: Mapping[str, Any]) -> JobOffer:
    require_permission(actor, RecruitmentPermissionCode.MANAGE_OFFERS, offer.organization_id)
    fields = {field: data[field] for field in _EDITABLE_FIELDS if field in data}
    _validate_references(fields)
    if not fields:
        return offer
    for field, value in fields.items():
        setattr(offer, field, value)
    offer.save(update_fields=[*fields, "updated_at"])
    return offer
