from django.db import transaction

from backend.apps.identity.models import Permission, Role, RolePermission
from backend.apps.matching.services.contracts import MATCHING_GRANTS, MATCHING_PERMISSIONS


@transaction.atomic
def seed_matching_rbac() -> None:
    permissions = {
        definition.code: Permission.objects.update_or_create(
            code=definition.code,
            defaults={"resource": definition.resource, "action": definition.action},
        )[0]
        for definition in MATCHING_PERMISSIONS
    }
    role_codes = {role_code for role_code, _ in MATCHING_GRANTS}
    roles = {role.code: role for role in Role.objects.filter(code__in=role_codes)}
    missing = role_codes - roles.keys()
    if missing:
        raise RuntimeError(f"Cannot seed matching RBAC: roles not seeded: {sorted(missing)}")
    for role_code, permission_code in MATCHING_GRANTS:
        RolePermission.objects.get_or_create(
            role=roles[role_code], permission=permissions[permission_code]
        )
