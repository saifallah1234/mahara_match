import uuid
from typing import Any

from django.db import models


class OfferSkill(models.Model):
    objects: models.Manager["OfferSkill"]
    # Q06: DM defines PK (offer_id, skill_id). Surrogate UUID + unique constraint is
    # provisional until the team decides the key strategy.
    id: Any = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer: Any = models.ForeignKey(
        "recruitment.JobOffer",
        on_delete=models.CASCADE,
        related_name="offer_skills",
    )
    skill: Any = models.ForeignKey(  # type: ignore[misc]
        "taxonomy.Skill",
        on_delete=models.PROTECT,
        related_name="offer_skills",
    )
    # G04/Q20: importance and level scales are undefined. Provisional free text.
    importance: Any = models.CharField(max_length=30, blank=True)
    required_level: Any = models.CharField(max_length=30, blank=True)
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
