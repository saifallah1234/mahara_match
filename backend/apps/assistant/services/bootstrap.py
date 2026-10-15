from django.db import transaction

from backend.apps.identity.models import Permission, Role, RoleCode, RolePermission


@transaction.atomic
def seed_assistant_rbac() -> None:
    permission, _ = Permission.objects.update_or_create(
        code="assistant.mock_interview.use",
        defaults={"resource": "assistant.mock_interview", "action": "use"},
    )
    RolePermission.objects.get_or_create(
        role=Role.objects.get(code=RoleCode.CANDIDATE), permission=permission
    )
