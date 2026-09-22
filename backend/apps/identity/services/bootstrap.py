from django.db import transaction

from backend.apps.identity.models import Permission, Role, RolePermission
from backend.apps.identity.services.contracts import (
    BASE_PERMISSIONS,
    BASE_ROLE_NAMES,
    BASELINE_GRANTS,
)


@transaction.atomic
def seed_identity_rbac() -> None:
    roles = {
        code: Role.objects.update_or_create(code=code, defaults={"name": name})[0]
        for code, name in BASE_ROLE_NAMES.items()
    }
    permissions = {
        definition.code: Permission.objects.update_or_create(
            code=definition.code,
            defaults={
                "resource": definition.resource,
                "action": definition.action,
            },
        )[0]
        for definition in BASE_PERMISSIONS
    }
    for role_code, permission_code in BASELINE_GRANTS:
        RolePermission.objects.get_or_create(
            role=roles[role_code],
            permission=permissions[permission_code],
        )
