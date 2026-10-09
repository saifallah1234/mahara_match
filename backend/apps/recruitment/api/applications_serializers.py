from rest_framework import serializers

from backend.apps.recruitment.models import Application, ApplicationStatus


class ApplicationReadSerializer(serializers.ModelSerializer[Application]):
    candidate_id = serializers.UUIDField(read_only=True)
    offer_id = serializers.UUIDField(read_only=True)
    offer_title = serializers.CharField(source="offer.title", read_only=True)
    cv_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "candidate_id",
            "offer_id",
            "offer_title",
            "cv_id",
            "status",
            "cover_letter",
            "applied_at",
            "withdrawn_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ApplicationSubmitSerializer(serializers.Serializer[dict[str, object]]):
    offer_id = serializers.UUIDField()
    cv_id = serializers.UUIDField()
    cover_letter = serializers.CharField(required=False, allow_blank=True)


class ApplicationTransitionSerializer(serializers.Serializer[dict[str, object]]):
    status = serializers.ChoiceField(choices=ApplicationStatus.values)
    reason = serializers.CharField(required=False, allow_blank=True)
