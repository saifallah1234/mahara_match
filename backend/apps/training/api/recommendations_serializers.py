from typing import Any

from rest_framework import serializers

from backend.apps.training.models import TrainingRecommendation


class TrainingRecommendationReadSerializer(serializers.ModelSerializer[TrainingRecommendation]):
    class Meta:
        model = TrainingRecommendation
        fields = (
            "id",
            "candidate_id",
            "program",
            "reason_json",
            "score",
            "model_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TrainingRecommendationCreateSerializer(serializers.Serializer[dict[str, Any]]):
    candidate_id = serializers.UUIDField()
    program_id = serializers.UUIDField()
    reason_json = serializers.JSONField(required=False)
    score = serializers.FloatField(min_value=0.0, max_value=100.0)
    model_version = serializers.CharField(max_length=50)
