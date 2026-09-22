from django.conf import settings
from django.db import models
from django.db.models import Q

from backend.common.models import UUIDTimestampedModel


class UserRole(UUIDTimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        "identity.Role",
        on_delete=models.PROTECT,
        related_name="user_assignments",
    )
    organization = models.ForeignKey(  # type: ignore[misc]
        "identity.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="role_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_roles"
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "role", "organization"),
                condition=Q(organization__isnull=False),
                name="user_roles_scoped_unique",
            ),
            models.UniqueConstraint(
                fields=("user", "role"),
                condition=Q(organization__isnull=True),
                name="user_roles_global_unique",
            ),
        ]
        indexes = [
            models.Index(fields=("user", "organization"), name="user_roles_user_org_idx"),
            models.Index(fields=("role", "organization"), name="user_roles_role_org_idx"),
        ]

    def __str__(self) -> str:
        scope = self.organization_id or "global"
        return f"{self.user_id}:{self.role_id}:{scope}"
