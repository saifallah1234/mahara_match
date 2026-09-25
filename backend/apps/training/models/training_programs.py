from typing import ClassVar

from django.db import models

from backend.common.models import UUIDTimestampedModel


class ProgramLevel(models.TextChoices):
    BEGINNER = "BEGINNER", "Beginner"
    INTERMEDIATE = "INTERMEDIATE", "Intermediate"
    ADVANCED = "ADVANCED", "Advanced"


class DeliveryMode(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    PRESENTIAL = "PRESENTIAL", "Presential"
    HYBRID = "HYBRID", "Hybrid"


class ProgramStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class TrainingProgram(UUIDTimestampedModel):
    objects: ClassVar[models.Manager] = models.Manager()
    organization_id: models.UUIDField = models.UUIDField(db_index=True)
    title: models.CharField = models.CharField(max_length=255)
    description: models.TextField = models.TextField(blank=True, default="")
    level: models.CharField = models.CharField(
        max_length=30, choices=ProgramLevel.choices, default=ProgramLevel.BEGINNER
    )
    delivery_mode: models.CharField = models.CharField(
        max_length=30, choices=DeliveryMode.choices, default=DeliveryMode.ONLINE
    )
    status: models.CharField = models.CharField(
        max_length=30, choices=ProgramStatus.choices, default=ProgramStatus.DRAFT
    )
    is_paid: models.BooleanField = models.BooleanField(default=False)
    price: models.DecimalField = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        app_label = "training"
        db_table = "training_programs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"
