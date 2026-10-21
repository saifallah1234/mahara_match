from rest_framework import serializers

from backend.apps.recruitment.models import Application, ApplicationStatus


class ApplicationReadSerializer(serializers.ModelSerializer[Application]):
    candidate_id = serializers.UUIDField(read_only=True)
    # Disclosed to the receiving organization only (ADR 0001).
    candidate_first_name = serializers.CharField(source="candidate.user.first_name", read_only=True)
    candidate_last_name = serializers.CharField(source="candidate.user.last_name", read_only=True)
    offer_id = serializers.UUIDField(read_only=True)
    offer_title = serializers.CharField(source="offer.title", read_only=True)
    cv_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "candidate_id",
            "candidate_first_name",
            "candidate_last_name",
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
