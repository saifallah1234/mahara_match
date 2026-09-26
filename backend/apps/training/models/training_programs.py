from typing import ClassVar

from django.db import models
from django.db.models import Q

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
    organization = models.ForeignKey(
        "identity.Organization", on_delete=models.PROTECT, related_name="training_programs"
    )
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
    is_free: models.BooleanField = models.BooleanField(default=True)
    price: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        app_label = "training"
        db_table = "training_programs"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(is_free=True, price=0) | Q(is_free=False, price__gt=0)),
                name="training_programs_free_price_consistent",
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"
