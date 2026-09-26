from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from backend.apps.identity.models import Permission, Role, RolePermission, User
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import BASELINE_GRANTS, IdentityPermissionCode
from backend.common.exceptions import (
    DomainNotFoundError,
    DomainPermissionError,
    DomainValidationError,
)


def list_role_permissions(actor: User) -> QuerySet[RolePermission]:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    return RolePermission.objects.select_related("role", "permission").order_by("created_at", "id")


def get_role_permission(actor: User, grant_id: UUID | str) -> RolePermission:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    try:
        return RolePermission.objects.select_related("role", "permission").get(id=grant_id)
    except RolePermission.DoesNotExist as exc:
        raise DomainNotFoundError("Permission grant not found.") from exc


@transaction.atomic
def grant_permission(
    actor: User,
    *,
    role_id: UUID,
    permission_id: UUID,
) -> RolePermission:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    try:
        role = Role.objects.get(id=role_id)
        permission = Permission.objects.get(id=permission_id)
    except (Role.DoesNotExist, Permission.DoesNotExist) as exc:
        raise DomainValidationError(details={"grant": ["Role or permission not found."]}) from exc
    try:
        return RolePermission.objects.create(role=role, permission=permission)
    except IntegrityError as exc:
        raise DomainValidationError(
            details={"grant": ["This permission is already granted."]}
        ) from exc


@transaction.atomic
def revoke_permission(actor: User, grant: RolePermission) -> None:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    if (grant.role.code, grant.permission.code) in BASELINE_GRANTS:
        raise DomainPermissionError("Baseline RBAC grants cannot be removed.")
    grant.delete()
