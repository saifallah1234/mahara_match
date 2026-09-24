from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from backend.apps.identity.models import OrganizationMember
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_members(
    actor: Any,
    organization_id: UUID | str,
) -> QuerySet[OrganizationMember]:
    require_permission(
        actor,
        IdentityPermissionCode.MANAGE_ORGANIZATIONS,
        organization_id,
    )

    return (
        OrganizationMember.objects
        .filter(organization_id=organization_id)
        .select_related("organization", "user")
        .order_by("created_at", "id")
    )


def get_member(
    actor: Any,
    organization_id: UUID | str,
    member_id: UUID | str,
) -> OrganizationMember:
    require_permission(
        actor,
        IdentityPermissionCode.MANAGE_ORGANIZATIONS,
        organization_id,
    )

    try:
        return (
            OrganizationMember.objects
            .select_related("organization", "user")
            .get(
                id=member_id,
                organization_id=organization_id,
            )
        )
    except OrganizationMember.DoesNotExist as exc:
        raise DomainNotFoundError("Organization member not found.") from exc


@transaction.atomic
def create_member(
    actor: Any,
    data: Mapping[str, Any],
) -> OrganizationMember:
    organization_id = data["organization"]
    require_permission(
        actor,
        IdentityPermissionCode.MANAGE_ORGANIZATIONS,
        organization_id,
    )

    try:
        return OrganizationMember.objects.create(**dict(data))
    except IntegrityError as exc:
        raise DomainValidationError(
            details={
                "user": [
                    "This user is already a member of this organization."
                ]
            }
        ) from exc


@transaction.atomic
def update_member(
    actor: Any,
    member: OrganizationMember,
    data: Mapping[str, Any],
) -> OrganizationMember:
    require_permission(
        actor,
        IdentityPermissionCode.MANAGE_ORGANIZATIONS,
        member.organization_id,
    )

    data = dict(data)

    for field in ("job_title", "joined_at"):
        if field in data:
            setattr(member, field, data[field])

    member.save(update_fields=[*data.keys(), "updated_at"])
    return member


@transaction.atomic
def remove_member(
    actor: Any,
    member: OrganizationMember,
) -> None:
    require_permission(
        actor,
        IdentityPermissionCode.MANAGE_ORGANIZATIONS,
        member.organization_id,
    )

    member.delete()