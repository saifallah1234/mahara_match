from typing import Any
from uuid import UUID
from collections.abc import Mapping

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from backend.apps.identity.models import Organization
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.apps.identity.models.organizations import VerificationStatus
from backend.common.exceptions import DomainNotFoundError
from backend.common.exceptions import DomainValidationError


def list_organizations(actor: Any) -> QuerySet[Organization]:
    require_permission(actor, IdentityPermissionCode.MANAGE_ORGANIZATIONS)

    return Organization.objects.select_related("parent").order_by("legal_name", "id")


def get_organization(actor: Any, organization_id: UUID | str) -> Organization:
    require_permission(actor, IdentityPermissionCode.MANAGE_ORGANIZATIONS)

    try:
        return Organization.objects.select_related("parent").get(id=organization_id)
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

    try:
        return Organization.objects.create(
            **data,
            verification_status="PENDING",
        )
    except IntegrityError as exc:
        raise DomainValidationError(
            details={
                "matricule_fiscal": [
                    "An organization with this matricule fiscal already exists."
                ]
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
                "matricule_fiscal": [
                    "An organization with this matricule fiscal already exists."
                ]
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
            details={
                "verification_status": [
                    "Only pending organizations can be verified."
                ]
            }
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
            details={
                "verification_status": [
                    "Only pending organizations can be rejected."
                ]
            }
        )

    organization.verification_status = VerificationStatus.REJECTED
    organization.save(update_fields=["verification_status", "updated_at"])

    return organization