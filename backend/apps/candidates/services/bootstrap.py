from django.db import transaction

from backend.apps.candidates.services.contracts import CandidatePermissionCode
from backend.apps.identity.models import Permission, Role, RoleCode, RolePermission


@transaction.atomic
def seed_candidates_rbac() -> None:
    role = Role.objects.get(code=RoleCode.RECRUITER)
    permission, _ = Permission.objects.update_or_create(
        code=CandidatePermissionCode.DISCOVER,
        defaults={"resource": "candidates.profile", "action": "discover"},
    )
    RolePermission.objects.get_or_create(role=role, permission=permission)
