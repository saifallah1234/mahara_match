from typing import Any, cast
from uuid import UUID

from django.db.models import Model, Q, QuerySet

from backend.apps.identity.models import User, UserRole
from backend.common.exceptions import DomainPermissionError


def organization_ids_with_permission(actor: User, permission_code: str) -> set[UUID] | None:
    """Organizations for which the actor holds the permission. None means unrestricted."""
    if not actor.is_active:
        return set()
    if actor.is_superuser:
        return None
    user_role_manager = cast(Any, UserRole.objects)
    ids = set(
        user_role_manager.filter(
            user=actor,
            role__permission_grants__permission__code=permission_code,
        )
        .filter(
            Q(organization__isnull=True)
            | Q(organization__members__user=actor, organization__deleted_at__isnull=True)
        )
        .values_list("organization_id", flat=True)
    )
    if None in ids:
        return None
    return {organization_id for organization_id in ids if organization_id is not None}


def restrict_to_organizations[M: Model](
    actor: User,
    queryset: QuerySet[M],
    permission_code: str,
    organization_lookup: str,
) -> QuerySet[M]:
    """Limit a queryset to the organizations the actor may access.

    `organization_lookup` is the ORM path to the owning organization id,
    e.g. "offer__organization_id".
    """
    scope = organization_ids_with_permission(actor, permission_code)
    if scope is None:
        return queryset
    if not scope:
        raise DomainPermissionError()
    return queryset.filter(**{f"{organization_lookup}__in": scope})
