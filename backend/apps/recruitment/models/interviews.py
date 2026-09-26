import uuid
from typing import Any

from django.conf import settings
from django.db import models


class Interview(models.Model):
    objects: models.Manager["Interview"]
    id: Any = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application: Any = models.ForeignKey(
        "recruitment.Application",
        on_delete=models.PROTECT,
        related_name="interviews",
    )
    scheduled_by: Any = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="scheduled_interviews",
    )
    # Q12/Q24: `type` and `status` have no defined values. Free text until agreed.
    type: Any = models.CharField(max_length=30)
    scheduled_at: Any = models.DateTimeField()
    duration_minutes: Any = models.PositiveIntegerField(null=True, blank=True)
    location_or_url: Any = models.TextField(blank=True)
    status: Any = models.CharField(max_length=30, db_index=True)
    feedback: Any = models.TextField(blank=True)
    application_id: uuid.UUID
    created_at: Any = models.DateTimeField(auto_now_add=True)
    updated_at: Any = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interviews"
        ordering = ("scheduled_at", "id")

    def __str__(self) -> str:
        return f"{self.application_id} @ {self.scheduled_at}"
