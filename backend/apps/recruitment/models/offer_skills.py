import uuid
from typing import Any

from django.db import models

from backend.apps.candidates.models.entities import SkillLevel


class OfferSkill(models.Model):
    objects: models.Manager["OfferSkill"]
    # Q06: UUID key plus unique offer/skill association.
    id: Any = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer: Any = models.ForeignKey(
        "recruitment.JobOffer",
        on_delete=models.CASCADE,
        related_name="offer_skills",
    )
    skill: Any = models.ForeignKey(
        "taxonomy.Skill",
        on_delete=models.PROTECT,
        related_name="offer_skills",
    )
    # Importance scale is still an owning contract.
    importance: Any = models.CharField(max_length=30, blank=True)
    required_level: Any = models.CharField(max_length=30, choices=SkillLevel.choices, blank=True)
    is_mandatory: Any = models.BooleanField(default=False)
    offer_id: uuid.UUID
    skill_id: uuid.UUID
    created_at: Any = models.DateTimeField(auto_now_add=True)
    updated_at: Any = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "offer_skills"
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["offer", "skill"],
                name="offer_skills_offer_skill_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.offer_id} -> {self.skill_id}"
