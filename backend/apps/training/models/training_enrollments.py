import uuid
from typing import ClassVar

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from backend.apps.training.models.training_sessions import TrainingSession
from backend.common.models import UUIDTimestampedModel


class EnrollmentStatus(models.TextChoices):
    REGISTERED = "REGISTERED", "Registered"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    DROPPED = "DROPPED", "Dropped"


class TrainingEnrollment(UUIDTimestampedModel):
    objects: ClassVar[models.Manager] = models.Manager()
    session: models.ForeignKey = models.ForeignKey(
        TrainingSession, on_delete=models.CASCADE, related_name="enrollments"
    )
    session_id: uuid.UUID  # Explicitly type the underlying foreign key ID for type checkers

    candidate_id: models.UUIDField = models.UUIDField(db_index=True)
    status: models.CharField = models.CharField(
        max_length=30, choices=EnrollmentStatus.choices, default=EnrollmentStatus.REGISTERED
    )
    enrolled_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    completion_rate: models.FloatField = models.FloatField(
        default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    completed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "training"
        db_table = "training_enrollments"
        unique_together = ("session", "candidate_id")

    def __str__(self) -> str:
        return f"Candidate {self.candidate_id} in Session {self.session_id}"
