from typing import Any

from django.conf import settings
from django.db import models

from backend.common.models import UUIDTimestampedModel


class Notification(UUIDTimestampedModel):
    user: Any = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    type: Any = models.CharField(max_length=100)
    title: Any = models.CharField(max_length=200)
    body: Any = models.TextField()
    payload_json: Any = models.JSONField(default=dict)
    read_at: Any = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ("-created_at", "id")


class AuditLog(UUIDTimestampedModel):
    actor_user: Any = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    actor_type: Any = models.CharField(max_length=20)
    agent_execution: Any = models.ForeignKey(
        "assistant.AgentExecution", on_delete=models.PROTECT, null=True, blank=True
    )
    action: Any = models.CharField(max_length=100)
    entity_type: Any = models.CharField(max_length=100)
    entity_id: Any = models.UUIDField()
    before_json: Any = models.JSONField(null=True, blank=True)
    after_json: Any = models.JSONField(null=True, blank=True)
    ip_address: Any = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ("-created_at", "id")
