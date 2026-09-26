from rest_framework import serializers

from backend.apps.recruitment.models import Application


class ApplicationReadSerializer(serializers.ModelSerializer[Application]):
    candidate_id = serializers.UUIDField(read_only=True)
    offer_id = serializers.UUIDField(read_only=True)
    cv_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "candidate_id",
            "offer_id",
            "cv_id",
            "status",
            "cover_letter",
            "applied_at",
            "withdrawn_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
