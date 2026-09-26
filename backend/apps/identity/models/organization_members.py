from django.conf import settings
from django.db import models

from backend.common.models import UUIDTimestampedModel


class OrganizationMember(UUIDTimestampedModel):
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organization_memberships",
    )
    job_title = models.CharField(
        max_length=150,
        blank=True,
    )
    joined_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "organization_members"
        ordering = ("organization_id", "user_id")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"], name="organization_members_org_user_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} - {self.organization_id}"
