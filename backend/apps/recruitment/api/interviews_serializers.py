from rest_framework import serializers

from backend.apps.recruitment.models import Interview, InterviewStatus, InterviewType


class InterviewReadSerializer(serializers.ModelSerializer[Interview]):
    application_id = serializers.UUIDField(read_only=True)
    scheduled_by_id = serializers.UUIDField(read_only=True)

    feedback = serializers.SerializerMethodField()

    def get_feedback(self, instance: Interview) -> str:
        request = self.context.get("request")
        if request and instance.application.candidate.user_id == request.user.id:
            return ""
        return str(instance.feedback)

    class Meta:
        model = Interview
        fields = (
            "id",
            "application_id",
            "scheduled_by_id",
            "type",
            "scheduled_at",
            "duration_minutes",
            "location_or_url",
            "status",
            "feedback",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class InterviewScheduleSerializer(serializers.Serializer[dict[str, object]]):
    application_id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=InterviewType.values)
    scheduled_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(required=False, min_value=1)
    location_or_url = serializers.CharField(required=False, allow_blank=True)


class InterviewTransitionSerializer(serializers.Serializer[dict[str, object]]):
    status = serializers.ChoiceField(choices=[InterviewStatus.COMPLETED, InterviewStatus.CANCELLED])
    feedback = serializers.CharField(required=False, allow_blank=True)
