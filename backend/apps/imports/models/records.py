from typing import Any

from django.db import models
from django.db.models import Q

from backend.common.models import UUIDTimestampedModel


class DataSource(UUIDTimestampedModel):
    name: Any = models.CharField(max_length=200)
    type: Any = models.CharField(max_length=30)
    base_url: Any = models.URLField(max_length=500, null=True, blank=True)  # noqa: DJ001
    is_authorized: Any = models.BooleanField(default=False)
    configuration_json: Any = models.JSONField(default=dict)
    acquisition_method: Any = models.CharField(max_length=100, blank=True)
    permission_evidence: Any = models.TextField(blank=True)
    reviewed_at: Any = models.DateTimeField(null=True, blank=True)
    expires_at: Any = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "data_sources"
        ordering = ("name", "id")


class ImportBatch(UUIDTimestampedModel):
    source: Any = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="batches")
    raw_document: Any = models.ForeignKey(
        "documents.Document", on_delete=models.PROTECT, null=True, blank=True
    )
    checksum: Any = models.CharField(max_length=128)
    status: Any = models.CharField(max_length=20)
    started_at: Any = models.DateTimeField()
    completed_at: Any = models.DateTimeField(null=True, blank=True)
    added_count: Any = models.PositiveIntegerField(default=0)
    updated_count: Any = models.PositiveIntegerField(default=0)
    unchanged_count: Any = models.PositiveIntegerField(default=0)
    rejected_count: Any = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "import_batches"
        ordering = ("-started_at", "id")
        indexes = [models.Index(fields=["source", "checksum"])]


class ImportRow(UUIDTimestampedModel):
    batch: Any = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="rows")
    row_number: Any = models.PositiveIntegerField()
    external_id: Any = models.CharField(max_length=255, blank=True)
    payload_json: Any = models.JSONField(default=dict)
    status: Any = models.CharField(max_length=20)
    error_code: Any = models.CharField(max_length=100, blank=True)
    error_message: Any = models.TextField(blank=True)
    job_offer: Any = models.ForeignKey(
        "recruitment.JobOffer", on_delete=models.PROTECT, null=True, blank=True
    )

    class Meta:
        db_table = "import_rows"
        ordering = ("row_number", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "row_number"], name="import_rows_batch_row_unique"
            ),
            models.CheckConstraint(
                condition=~Q(status="REJECTED") | ~Q(error_code=""),
                name="import_rows_rejection_has_error",
            ),
        ]
