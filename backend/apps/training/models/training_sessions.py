import uuid
from typing import ClassVar

from django.db import models

from backend.apps.training.models.training_programs import TrainingProgram
from backend.common.models import UUIDTimestampedModel


class SessionStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planned"
    ONGOING = "ONGOING", "Ongoing"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class TrainingSession(UUIDTimestampedModel):
    objects: ClassVar[models.Manager] = models.Manager()
    program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name="sessions")
    program_id: uuid.UUID  # Explicitly type the underlying foreign key ID for type checkers

    start_date: models.DateTimeField = models.DateTimeField()
    end_date: models.DateTimeField = models.DateTimeField()
    capacity: models.PositiveIntegerField = models.PositiveIntegerField()
    location_or_url: models.CharField = models.CharField(max_length=500)
    registration_deadline: models.DateTimeField = models.DateTimeField()
    status: models.CharField = models.CharField(
        max_length=30, choices=SessionStatus.choices, default=SessionStatus.PLANNED
    )

    class Meta:
        app_label = "training"
        db_table = "training_sessions"
        ordering = ["start_date"]

    def __str__(self) -> str:
        return f"Session {self.id} for Program {self.program_id}"
