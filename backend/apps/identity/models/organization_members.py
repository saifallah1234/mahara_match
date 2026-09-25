from django.conf import settings
from django.db import models


class OrganizationMember(models.Model):
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
    pk = models.CompositePrimaryKey("organization_id", "user_id")

    class Meta:
        db_table = "organization_members"
        ordering = ("organization_id", "user_id")

    def __str__(self) -> str:
        return f"{self.user_id} - {self.organization_id}"
