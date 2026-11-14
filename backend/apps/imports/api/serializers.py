from typing import Any

from rest_framework import serializers

from backend.apps.imports.models import DataSource, ImportBatch, ImportRow


class SourceReadSerializer(serializers.ModelSerializer[DataSource]):
    class Meta:
        model = DataSource
        fields = (
            "id",
            "name",
            "type",
            "base_url",
            "is_authorized",
            "configuration_json",
            "acquisition_method",
            "permission_evidence",
            "reviewed_at",
            "expires_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SourceWriteSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=200)
    type = serializers.ChoiceField(choices=("API", "CSV", "MANUAL_FILE", "WEB_SCRAPING"))
    base_url = serializers.URLField(max_length=500, required=False, allow_null=True)
    configuration_json = serializers.JSONField(required=False)


class SourceAuthorizationSerializer(serializers.Serializer[dict[str, Any]]):
    acquisition_method = serializers.CharField(max_length=100)
    permission_evidence = serializers.CharField()
    expires_at = serializers.DateTimeField()


class BatchReadSerializer(serializers.ModelSerializer[ImportBatch]):
    class Meta:
        model = ImportBatch
        fields = (
            "id",
            "source_id",
            "raw_document_id",
            "checksum",
            "status",
            "started_at",
            "completed_at",
            "added_count",
            "updated_count",
            "unchanged_count",
            "rejected_count",
            "created_at",
        )
        read_only_fields = fields


class RowReadSerializer(serializers.ModelSerializer[ImportRow]):
    class Meta:
        model = ImportRow
        fields = (
            "id",
            "batch_id",
            "row_number",
            "external_id",
            "payload_json",
            "status",
            "error_code",
            "error_message",
            "job_offer_id",
            "created_at",
        )
        read_only_fields = fields
