from django.db import models

from backend.common.models import UUIDTimestampedModel


class RolePermission(UUIDTimestampedModel):
    role = models.ForeignKey(
        "identity.Role",
        on_delete=models.PROTECT,
        related_name="permission_grants",
    )
    permission = models.ForeignKey(
        "identity.Permission",
        on_delete=models.PROTECT,
        related_name="role_grants",
    )

    class Meta:
        db_table = "role_permissions"
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("role", "permission"),
                name="role_permissions_role_permission_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.role_id}:{self.permission_id}"
