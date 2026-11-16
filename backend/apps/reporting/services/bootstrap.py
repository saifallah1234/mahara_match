# Placement: backend/apps/reporting/services/bootstrap.py
from django.db import transaction

from backend.apps.identity.models import Permission, Role, RolePermission
from backend.apps.reporting.services.contracts import REPORTING_GRANTS, REPORTING_PERMISSIONS


@transaction.atomic
def seed_reporting_rbac() -> None:
    permissions = {
        item.code: Permission.objects.update_or_create(
            code=item.code, defaults={"resource": item.resource, "action": item.action}
        )[0]
        for item in REPORTING_PERMISSIONS
    }
    for role_code, permission_code in REPORTING_GRANTS:
        RolePermission.objects.get_or_create(
            role=Role.objects.get(code=role_code), permission=permissions[permission_code]
        )
