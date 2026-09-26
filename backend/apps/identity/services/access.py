from uuid import UUID

from django.db.models import Q

from backend.apps.identity.models import User, UserRole
from backend.common.exceptions import DomainPermissionError


def effective_permission_codes(user: User, organization_id: UUID | str | None = None) -> set[str]:
    if not user.is_active:
        return set()
    if user.is_superuser:
        return {"*"}

    assignments = UserRole.objects.filter(user=user).filter(
        Q(organization__isnull=True)
        | Q(organization__members__user=user, organization__deleted_at__isnull=True)
    )
    if organization_id is not None:
        assignments = assignments.filter(
            Q(organization_id__isnull=True) | Q(organization_id=organization_id)
        )

    return set(assignments.values_list("role__permission_grants__permission__code", flat=True)) - {
        None
    }


def has_permission(
    user: User, permission_code: str, organization_id: UUID | str | None = None
) -> bool:
    permission_codes = effective_permission_codes(user, organization_id)
    return "*" in permission_codes or permission_code in permission_codes


def require_permission(
    user: User,
    permission_code: str,
    organization_id: UUID | str | None = None,
) -> None:
    if not has_permission(user, permission_code, organization_id):
        raise DomainPermissionError()
