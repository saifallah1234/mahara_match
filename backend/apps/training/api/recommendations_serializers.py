from rest_framework import serializers

from backend.apps.training.models import TrainingRecommendation


class TrainingRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRecommendation
        fields = [
            "id",
            "candidate_id",
            "program",
            "reason_json",
            "score",
            "model_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
