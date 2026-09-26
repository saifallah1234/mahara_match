from rest_framework import serializers

from backend.apps.recruitment.models import ApplicationStatusHistory


class ApplicationStatusHistoryReadSerializer(serializers.ModelSerializer[ApplicationStatusHistory]):
    application_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ApplicationStatusHistory
        fields = ("id", "application_id", "status", "reason", "changed_at")
        read_only_fields = fields
