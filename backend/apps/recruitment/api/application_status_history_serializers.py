from rest_framework import serializers

from backend.apps.recruitment.models import ApplicationStatusHistory


class ApplicationStatusHistoryReadSerializer(serializers.ModelSerializer[ApplicationStatusHistory]):
    application_id = serializers.UUIDField(read_only=True)
    reason = serializers.SerializerMethodField()

    def get_reason(self, instance: ApplicationStatusHistory) -> str:
        request = self.context.get("request")
        if request and instance.application.candidate.user_id == request.user.id:
            return ""
        return str(instance.reason)

    class Meta:
        model = ApplicationStatusHistory
        fields = ("id", "application_id", "status", "reason", "changed_at")
        read_only_fields = fields
