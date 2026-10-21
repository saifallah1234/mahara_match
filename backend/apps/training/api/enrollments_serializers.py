from typing import Any

from rest_framework import serializers

from backend.apps.training.models import TrainingEnrollment


class TrainingEnrollmentReadSerializer(serializers.ModelSerializer[TrainingEnrollment]):
    # Disclosed to the training provider only (ADR 0001).
    candidate_first_name = serializers.CharField(source="candidate.user.first_name", read_only=True)
    candidate_last_name = serializers.CharField(source="candidate.user.last_name", read_only=True)
    # Kept on the enrollment so a finished session still has a title after it leaves the catalogue.
    program_title = serializers.CharField(source="session.program.title", read_only=True)
    session_start_date = serializers.DateTimeField(source="session.start_date", read_only=True)

    class Meta:
        model = TrainingEnrollment
        fields = (
            "id",
            "session",
            "candidate_id",
            "candidate_first_name",
            "candidate_last_name",
            "program_title",
            "session_start_date",
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
