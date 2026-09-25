from typing import Any

from rest_framework import serializers

from backend.apps.training.models import TrainingEnrollment


class TrainingEnrollmentReadSerializer(serializers.ModelSerializer[TrainingEnrollment]):
    class Meta:
        model = TrainingEnrollment
        fields = (
            "id",
            "session",
            "candidate_id",
            "status",
            "enrolled_at",
            "completion_rate",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TrainingEnrollmentCreateSerializer(serializers.Serializer[dict[str, Any]]):
    session_id = serializers.UUIDField()
    # Optional: a training manager/admin may enroll someone else. A candidate
    # enrolling themselves omits this and the service defaults it to the actor.
    candidate_id = serializers.UUIDField(required=False)


class TrainingEnrollmentProgressSerializer(serializers.Serializer[dict[str, Any]]):
    completion_rate = serializers.FloatField(min_value=0.0, max_value=100.0)
