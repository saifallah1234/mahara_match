from rest_framework import serializers

from backend.apps.training.models import TrainingEnrollment


class TrainingEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingEnrollment
        fields = [
            "id",
            "session",
            "candidate_id",
            "status",
            "enrolled_at",
            "completion_rate",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "enrolled_at", "completed_at", "created_at", "updated_at"]
