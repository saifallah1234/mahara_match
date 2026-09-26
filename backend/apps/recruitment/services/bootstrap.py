from django.db import transaction

from backend.apps.identity.models import Permission, Role, RolePermission
from backend.apps.recruitment.services.contracts import (
    RECRUITMENT_GRANTS,
    RECRUITMENT_PERMISSIONS,
)


@transaction.atomic
def seed_recruitment_rbac() -> None:
    permissions = {
        definition.code: Permission.objects.update_or_create(
            code=definition.code,
            defaults={"resource": definition.resource, "action": definition.action},
        )[0]
        for definition in RECRUITMENT_PERMISSIONS
    }
    role_codes = {role_code for role_code, _ in RECRUITMENT_GRANTS}
    roles = {role.code: role for role in Role.objects.filter(code__in=role_codes)}
    missing = role_codes - roles.keys()
    if missing:
        raise RuntimeError(f"Cannot seed recruitment RBAC: roles not seeded: {sorted(missing)}")
    for role_code, permission_code in RECRUITMENT_GRANTS:
        RolePermission.objects.get_or_create(
            role=roles[role_code], permission=permissions[permission_code]
        )
