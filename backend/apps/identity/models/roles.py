from django.db import models

from backend.common.models import UUIDTimestampedModel


class RoleCode(models.TextChoices):
    CANDIDATE = "CANDIDATE", "Candidate"
    RECRUITER = "RECRUITER", "Recruiter"
    TRAINING_MANAGER = "TRAINING_MANAGER", "Training manager"
    MINISTRY_MANAGER = "MINISTRY_MANAGER", "Ministry manager"
    ADMIN = "ADMIN", "Administrator"


class Role(UUIDTimestampedModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        "identity.Permission",
        through="identity.RolePermission",
        related_name="roles",
    )

    class Meta:
        db_table = "roles"
        ordering = ("code",)

    def __str__(self) -> str:
        return self.code
