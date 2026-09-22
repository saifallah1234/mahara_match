from django.db import models

from backend.common.models import UUIDTimestampedModel


class Permission(UUIDTimestampedModel):
    code = models.CharField(max_length=150, unique=True)
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=50)

    class Meta:
        db_table = "permissions"
        ordering = ("code",)
        constraints = [
            models.UniqueConstraint(
                fields=("resource", "action"),
                name="permissions_resource_action_unique",
            )
        ]

    def __str__(self) -> str:
        return self.code
