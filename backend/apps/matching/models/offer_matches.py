import uuid
from typing import Any

from django.db import models
from django.db.models import Q


class OfferMatch(models.Model):
    objects: models.Manager["OfferMatch"]
    id: Any = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate: Any = models.ForeignKey(
        "candidates.CandidateProfile",
        on_delete=models.CASCADE,
        related_name="offer_matches",
    )
    offer: Any = models.ForeignKey(
        "recruitment.JobOffer",
        on_delete=models.CASCADE,
        related_name="offer_matches",
    )
    model_version: Any = models.CharField(max_length=50)
    # Q26: score semantics unknown. Decimal(5,2) mirrors completion_score (0-100).
    # Sub-scores are nullable so missing data is never replaced by a fabricated score.
    overall_score: Any = models.DecimalField(max_digits=5, decimal_places=2)
    skill_score: Any = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    experience_score: Any = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    location_score: Any = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    explanation_json: Any = models.JSONField(default=dict, blank=True)
    calculated_at: Any = models.DateTimeField()
    candidate_id: uuid.UUID
    offer_id: uuid.UUID
    created_at: Any = models.DateTimeField(auto_now_add=True)
    updated_at: Any = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "offer_matches"
        ordering = ("-calculated_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "offer", "model_version"],
                name="offer_matches_candidate_offer_version_unique",
            ),
            models.CheckConstraint(
                condition=Q(overall_score__gte=0, overall_score__lte=100),
                name="offer_matches_overall_score_0_100",
            ),
            models.CheckConstraint(
                condition=Q(skill_score__isnull=True) | Q(skill_score__gte=0, skill_score__lte=100),
                name="offer_matches_skill_score_0_100",
            ),
            models.CheckConstraint(
                condition=Q(experience_score__isnull=True)
                | Q(experience_score__gte=0, experience_score__lte=100),
                name="offer_matches_experience_score_0_100",
            ),
            models.CheckConstraint(
                condition=Q(location_score__isnull=True)
                | Q(location_score__gte=0, location_score__lte=100),
                name="offer_matches_location_score_0_100",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.candidate_id} ~ {self.offer_id} ({self.model_version})"
