from rest_framework import serializers

from backend.apps.training.models import TrainingSession


class TrainingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSession
        fields = [
            "id",
            "program",
            "start_date",
            "end_date",
            "capacity",
            "location_or_url",
            "registration_deadline",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
