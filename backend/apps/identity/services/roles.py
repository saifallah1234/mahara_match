from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from backend.apps.identity.models import Role
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.common.exceptions import DomainNotFoundError


def list_roles(actor: Any) -> QuerySet[Role]:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    return Role.objects.order_by("code")


def get_role(actor: Any, role_id: UUID | str) -> Role:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    try:
        return Role.objects.get(id=role_id)
    except Role.DoesNotExist as exc:
        raise DomainNotFoundError("Role not found.") from exc


@transaction.atomic
def update_role(actor: Any, role: Role, data: Mapping[str, Any]) -> Role:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    for field in ("name", "description"):
        if field in data:
            setattr(role, field, data[field])
    role.save(update_fields=[*data.keys(), "updated_at"])
    return role
