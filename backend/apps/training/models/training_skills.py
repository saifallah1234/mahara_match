import uuid
from typing import ClassVar

from django.db import models

from backend.apps.candidates.models.entities import SkillLevel
from backend.apps.training.models.training_programs import TrainingProgram
from backend.common.models import UUIDTimestampedModel


class TrainingSkillPurpose(models.TextChoices):
    PREREQUISITE = "PREREQUISITE", "Prerequisite"
    TAUGHT = "TAUGHT", "Taught"


class TrainingSkill(UUIDTimestampedModel):
    objects: ClassVar[models.Manager] = models.Manager()
    program = models.ForeignKey(
        TrainingProgram, on_delete=models.PROTECT, related_name="program_skills"
    )
    program_id: uuid.UUID  # Explicitly type the underlying foreign key ID for type checkers

    skill = models.ForeignKey(
        "taxonomy.Skill", on_delete=models.PROTECT, related_name="training_program_links"
    )
    target_level: models.CharField = models.CharField(max_length=20, choices=SkillLevel.choices)
    purpose: models.CharField = models.CharField(
        max_length=20, choices=TrainingSkillPurpose.choices, default=TrainingSkillPurpose.TAUGHT
    )

    class Meta:
        app_label = "training"
        db_table = "training_skills"
        constraints = [
            models.UniqueConstraint(
                fields=("program", "skill", "purpose"), name="training_skill_program_purpose_unique"
            )
        ]

    def __str__(self) -> str:
        return f"Skill {self.skill_id} -> Program {self.program_id}"
