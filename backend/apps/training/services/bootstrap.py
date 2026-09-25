from django.db import transaction

from backend.apps.identity.models import Permission, Role, RolePermission
from backend.apps.training.services.contracts import BASE_PERMISSIONS, BASELINE_GRANTS


@transaction.atomic
def seed_training_rbac() -> None:
    """Registers training permissions and grants them to existing identity roles.

    Roles are owned and created by ``identity.services.bootstrap.seed_identity_rbac``,
    which must run first.
    """
    permissions = {
        definition.code: Permission.objects.update_or_create(
            code=definition.code,
            defaults={"resource": definition.resource, "action": definition.action},
        )[0]
        for definition in BASE_PERMISSIONS
    }

    role_codes = {role_code for role_code, _ in BASELINE_GRANTS}
    roles = {role.code: role for role in Role.objects.filter(code__in=role_codes)}
    missing = role_codes - roles.keys()
    if missing:
        raise RuntimeError(
            f"Cannot seed training RBAC: identity roles not seeded yet: {sorted(missing)}"
        )

    for role_code, permission_code in BASELINE_GRANTS:
        RolePermission.objects.get_or_create(
            role=roles[role_code],
            permission=permissions[permission_code],
        )
