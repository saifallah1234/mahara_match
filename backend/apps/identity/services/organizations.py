from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from backend.apps.identity.models import Organization
from backend.apps.identity.models.organizations import VerificationStatus
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def _validate_hierarchy(
    *,
    organization: Organization | None,
    organization_type: str,
    parent_id: UUID | None,
) -> None:
    if parent_id is None:
        return
    if organization_type != "SUBSIDIARY":
        raise DomainValidationError(
            details={"parent_id": ["Only subsidiary organizations can have a parent."]}
        )

    try:
        parent = Organization.objects.get(id=parent_id, deleted_at__isnull=True)
    except Organization.DoesNotExist as exc:
        raise DomainValidationError(
            details={"parent_id": ["Parent organization not found."]}
        ) from exc

    if parent.type != "COMPANY":
        raise DomainValidationError(
            details={"parent_id": ["A subsidiary's parent must be a company."]}
        )
    if organization is not None and parent.id == organization.id:
        raise DomainValidationError(
            details={"parent_id": ["An organization cannot be its own parent."]}
        )


def _validate_unique_identifiers(
    data: Mapping[str, Any],
    organization: Organization | None = None,
) -> None:
    for field in ("matricule_fiscal", "registration_number"):
        value = data.get(field)
        if value is None:
            continue
        queryset = Organization.objects.filter(**{field: value})
        if organization is not None:
            queryset = queryset.exclude(pk=organization.pk)
        if queryset.exists():
            label = "matricule fiscal" if field == "matricule_fiscal" else "registration number"
            raise DomainValidationError(
                details={field: [f"An organization with this {label} already exists."]}
            )


def list_organizations(actor: Any) -> QuerySet[Organization]:
    require_permission(actor, IdentityPermissionCode.MANAGE_ORGANIZATIONS)

    return (
        Organization.objects.filter(deleted_at__isnull=True)
        .select_related("parent")
        .order_by("legal_name", "id")
    )


def get_organization(actor: Any, organization_id: UUID | str) -> Organization:
    require_permission(actor, IdentityPermissionCode.MANAGE_ORGANIZATIONS)

    try:
        return Organization.objects.select_related("parent").get(
            id=organization_id, deleted_at__isnull=True
        )
    except Organization.DoesNotExist as exc:
        raise DomainNotFoundError("Organization not found.") from exc


@transaction.atomic
def create_organization(
    actor: Any,
    data: Mapping[str, Any],
) -> Organization:
    require_permission(actor, IdentityPermissionCode.MANAGE_ORGANIZATIONS)

    data = dict(data)
    data.pop("verification_status", None)
    if data.get("registration_number") == "":
        data["registration_number"] = None
    _validate_hierarchy(
        organization=None,
        organization_type=data["type"],
        parent_id=data.get("parent_id"),
    )
    _validate_unique_identifiers(data)

    try:
        return Organization.objects.create(
            **data,
            verification_status="PENDING",
        )
    except IntegrityError as exc:
        raise DomainValidationError(
            details={
                "matricule_fiscal": ["An organization with this matricule fiscal already exists."]
            }
        ) from exc


@transaction.atomic
def update_organization(
    actor: Any,
    organization: Organization,
    data: Mapping[str, Any],
) -> Organization:
    require_permission(actor, IdentityPermissionCode.MANAGE_ORGANIZATIONS)

    data = dict(data)
    data.pop("verification_status", None)
    if data.get("registration_number") == "":
        data["registration_number"] = None

    organization_type = data.get("type", organization.type)
    parent_id = data.get("parent_id", organization.parent_id)
    _validate_hierarchy(
        organization=organization,
        organization_type=organization_type,
        parent_id=parent_id,
    )
    _validate_unique_identifiers(data, organization)

    if "parent_id" in data:
        organization.parent_id = data.pop("parent_id")

    for field in (
        "type",
        "legal_name",
        "registration_number",
        "description",
        "website_url",
        "logo_uri",
        "matricule_fiscal",
        "governorate",
        "city",
        "address_line",
    ):
        if field in data:
            setattr(organization, field, data[field])

    try:
        organization.save(update_fields=[*data.keys(), "parent_id", "updated_at"])
    except IntegrityError as exc:
        raise DomainValidationError(
            details={
                "matricule_fiscal": ["An organization with this matricule fiscal already exists."]
            }
        ) from exc

    return organization


@transaction.atomic
def verify_organization(
    actor: Any,
    organization: Organization,
) -> Organization:
    require_permission(actor, IdentityPermissionCode.MANAGE_ORGANIZATIONS)

    if organization.verification_status != VerificationStatus.PENDING:
        raise DomainValidationError(
            details={"verification_status": ["Only pending organizations can be verified."]}
        )

    organization.verification_status = VerificationStatus.VERIFIED
    organization.save(update_fields=["verification_status", "updated_at"])

    return organization


@transaction.atomic
def reject_organization(
    actor: Any,
    organization: Organization,
) -> Organization:
    require_permission(actor, IdentityPermissionCode.MANAGE_ORGANIZATIONS)

    if organization.verification_status != VerificationStatus.PENDING:
        raise DomainValidationError(
            details={"verification_status": ["Only pending organizations can be rejected."]}
        )

    organization.verification_status = VerificationStatus.REJECTED
    organization.save(update_fields=["verification_status", "updated_at"])

    return organization
