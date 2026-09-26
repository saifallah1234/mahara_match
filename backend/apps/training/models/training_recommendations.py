import uuid
from typing import ClassVar

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from backend.apps.training.models.training_programs import TrainingProgram
from backend.common.models import UUIDTimestampedModel


class TrainingRecommendation(UUIDTimestampedModel):
    objects: ClassVar[models.Manager] = models.Manager()
    candidate = models.ForeignKey(
        "candidates.CandidateProfile",
        on_delete=models.PROTECT,
        related_name="training_recommendations",
    )
    program = models.ForeignKey(
        TrainingProgram, on_delete=models.PROTECT, related_name="recommendations"
    )
    program_id: uuid.UUID  # Explicitly type the underlying foreign key ID for type checkers

    reason_json: models.JSONField = models.JSONField(default=dict)
    score: models.FloatField = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    model_version: models.CharField = models.CharField(max_length=50)

    class Meta:
        app_label = "training"
        db_table = "training_recommendations"
        ordering = ["-score"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__gte=0, score__lte=100),
                name="training_recommendation_score_range",
            )
        ]

    def __str__(self) -> str:
        return f"Recommendation for Candidate {self.candidate_id} - Score: {self.score}"
