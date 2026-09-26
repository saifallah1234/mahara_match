import uuid
from typing import Any

from django.db import models


class ApplicationStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    PRESELECTED = "PRESELECTED", "Preselected"
    INTERVIEW = "INTERVIEW", "Interview"
    OFFERED = "OFFERED", "Offered"
    HIRED = "HIRED", "Hired"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class Application(models.Model):
    objects: models.Manager["Application"]
    id: Any = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate: Any = models.ForeignKey(
        "candidates.CandidateProfile",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    offer: Any = models.ForeignKey(
        "recruitment.JobOffer",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    # The service layer must check that this CV belongs to `candidate` (DM section 7).
    cv: Any = models.ForeignKey(
        "candidates.CV",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    # Transitions are validated by the service, never by a plain PATCH (Q12).
    status: Any = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
        db_index=True,
    )
    cover_letter: Any = models.TextField(blank=True)
    applied_at: Any = models.DateTimeField(null=True, blank=True)
    withdrawn_at: Any = models.DateTimeField(null=True, blank=True)
    candidate_id: uuid.UUID
    offer_id: uuid.UUID
    created_at: Any = models.DateTimeField(auto_now_add=True)
    updated_at: Any = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "applications"
        ordering = ("created_at", "id")
        constraints = [
            # Q12: no reapplication after any final state.
            models.UniqueConstraint(
                fields=["candidate", "offer"],
                name="applications_candidate_offer_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.candidate_id} -> {self.offer_id} ({self.status})"
