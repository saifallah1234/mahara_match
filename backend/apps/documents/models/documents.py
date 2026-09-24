"""Stored-file metadata."""

from django.conf import settings
from django.db import models

from backend.common.models import UUIDTimestampedModel


class Document(UUIDTimestampedModel):
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="documents"
    )
    type = models.CharField(max_length=30)
    storage_uri = models.CharField(max_length=1024)
    file_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=150)
    size_bytes = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=128)
    scan_status = models.CharField(max_length=30)
    uploaded_at = models.DateTimeField()

    class Meta:
        db_table = "documents"
        ordering = ("-uploaded_at", "id")

    def __str__(self) -> str:
        return self.file_name
