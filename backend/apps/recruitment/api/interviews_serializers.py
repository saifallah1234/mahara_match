from rest_framework import serializers

from backend.apps.recruitment.models import Interview


class InterviewReadSerializer(serializers.ModelSerializer[Interview]):
    application_id = serializers.UUIDField(read_only=True)
    scheduled_by_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Interview
        fields = (
            "id",
            "application_id",
            "scheduled_by_id",
            "type",
            "scheduled_at",
            "duration_minutes",
            "location_or_url",
            "status",
            "feedback",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
