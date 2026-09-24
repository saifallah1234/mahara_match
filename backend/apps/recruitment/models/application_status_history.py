import uuid
from typing import Any

from django.db import models

from backend.apps.recruitment.models.applications import ApplicationStatus


class ApplicationStatusHistory(models.Model):
    objects: models.Manager["ApplicationStatusHistory"]
    id: Any = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application: Any = models.ForeignKey(
        "recruitment.Application",
        on_delete=models.PROTECT,
        related_name="status_history",
    )
    status: Any = models.CharField(max_length=20, choices=ApplicationStatus.choices)
    reason: Any = models.TextField(blank=True)
    application_id: uuid.UUID
    # Append-only: written by the transition service, never by callers.
    changed_at: Any = models.DateTimeField(auto_now_add=True)
    created_at: Any = models.DateTimeField(auto_now_add=True)
    updated_at: Any = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "application_status_history"
        ordering = ("changed_at", "id")

    def __str__(self) -> str:
        return f"{self.application_id}: {self.status}"
