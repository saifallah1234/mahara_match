from rest_framework import serializers

from backend.apps.matching.models import OfferMatch


class OfferMatchReadSerializer(serializers.ModelSerializer[OfferMatch]):
    candidate_id = serializers.UUIDField(read_only=True)
    offer_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = OfferMatch
        fields = (
            "id",
            "candidate_id",
            "offer_id",
            "model_version",
            "overall_score",
            "skill_score",
            "experience_score",
            "location_score",
            "explanation_json",
            "calculated_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
