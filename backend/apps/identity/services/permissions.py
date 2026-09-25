from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from backend.apps.identity.models import Permission
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError

"""
This file contains the service functions for managing permissions.

list_permissions(actor)
Checks that the current user has MANAGE_RBAC, then returns all permissions ordered by code.
get_permission(actor, permission_id)
Checks MANAGE_RBAC, then fetches one permission by ID. If it does not exist, it raises DomainNotFoundError.
create_permission(actor, data)
Checks MANAGE_RBAC, then creates a new permission.
"""

def list_permissions(actor: Any) -> QuerySet[Permission]:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    return Permission.objects.order_by("code")


def get_permission(actor: Any, permission_id: UUID | str) -> Permission:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    try:
        return Permission.objects.get(id=permission_id)
    except Permission.DoesNotExist as exc:
        raise DomainNotFoundError("Permission not found.") from exc


@transaction.atomic
def create_permission(actor: Any, data: Mapping[str, Any]) -> Permission:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    try:
        return Permission.objects.create(**data)
    except IntegrityError as exc:
        raise DomainValidationError(
            details={"code": ["The permission code or resource/action pair already exists."]}
        ) from exc
