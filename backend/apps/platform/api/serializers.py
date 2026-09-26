from rest_framework import serializers

from backend.apps.platform.models import AuditLog, Notification


class NotificationReadSerializer(serializers.ModelSerializer[Notification]):
    class Meta:
        model = Notification
        fields = ("id", "type", "title", "body", "payload_json", "read_at", "created_at")
        read_only_fields = fields


class AuditReadSerializer(serializers.ModelSerializer[AuditLog]):
    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor_user_id",
            "actor_type",
            "agent_execution_id",
            "action",
            "entity_type",
            "entity_id",
            "before_json",
            "after_json",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields
