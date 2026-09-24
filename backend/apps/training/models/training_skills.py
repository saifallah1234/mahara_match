import uuid
from typing import ClassVar

from django.db import models

from backend.apps.training.models.training_programs import TrainingProgram
from backend.common.models import UUIDTimestampedModel


class TrainingSkill(UUIDTimestampedModel):
    objects: ClassVar[models.Manager] = models.Manager()
    program: models.ForeignKey = models.ForeignKey(
        TrainingProgram, on_delete=models.CASCADE, related_name="program_skills"
    )
    program_id: uuid.UUID  # Explicitly type the underlying foreign key ID for type checkers

    skill_id: models.UUIDField = models.UUIDField(db_index=True)
    target_level: models.CharField = models.CharField(max_length=50)

    class Meta:
        app_label = "training"
        db_table = "training_skills"
        unique_together = ("program", "skill_id")

    def __str__(self) -> str:
        return f"Skill {self.skill_id} -> Program {self.program_id}"
