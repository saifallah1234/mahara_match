from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from backend.common.models import UUIDTimestampedModel


class Conversation(UUIDTimestampedModel):
    user: Any = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    title: Any = models.CharField(max_length=200, blank=True)
    status: Any = models.CharField(max_length=20, default="ACTIVE")
    started_at: Any = models.DateTimeField(default=timezone.now)
    last_message_at: Any = models.DateTimeField(null=True, blank=True)
    deleted_at: Any = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conversations"
        ordering = ("-started_at", "id")


class ConversationMessage(UUIDTimestampedModel):
    conversation: Any = models.ForeignKey(
        Conversation, on_delete=models.PROTECT, related_name="messages"
    )
    sender_type: Any = models.CharField(max_length=20)
    content: Any = models.TextField()
    intent: Any = models.CharField(max_length=100, blank=True)
    citations_json: Any = models.JSONField(default=list)

    class Meta:
        db_table = "conversation_messages"
        ordering = ("created_at", "id")


class AgentExecution(UUIDTimestampedModel):
    request_message: Any = models.ForeignKey(
        ConversationMessage, on_delete=models.PROTECT, related_name="agent_requests"
    )
    response_message: Any = models.ForeignKey(
        ConversationMessage,
        on_delete=models.PROTECT,
        related_name="agent_responses",
        null=True,
        blank=True,
    )
    route: Any = models.CharField(max_length=100)
    status: Any = models.CharField(max_length=20)
    agent_version: Any = models.CharField(max_length=100)
    latency_ms: Any = models.PositiveIntegerField(null=True, blank=True)
    error_code: Any = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "agent_executions"
        ordering = ("-created_at", "id")


class AgentToolCall(UUIDTimestampedModel):
    execution: Any = models.ForeignKey(
        AgentExecution, on_delete=models.PROTECT, related_name="tool_calls"
    )
    tool_name: Any = models.CharField(max_length=100)
    input_json: Any = models.JSONField(default=dict)
    output_summary_json: Any = models.JSONField(default=dict)
    status: Any = models.CharField(max_length=20)
    latency_ms: Any = models.PositiveIntegerField(null=True, blank=True)
    error_code: Any = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "agent_tool_calls"
        ordering = ("created_at", "id")


class AgentAction(UUIDTimestampedModel):
    execution: Any = models.ForeignKey(
        AgentExecution, on_delete=models.PROTECT, related_name="actions"
    )
    action_type: Any = models.CharField(max_length=100)
    target_type: Any = models.CharField(max_length=100)
    target_id: Any = models.UUIDField(null=True, blank=True)
    status: Any = models.CharField(max_length=20, default="PROPOSED")
    idempotency_key: Any = models.CharField(max_length=255, unique=True)
    confirmed_at: Any = models.DateTimeField(null=True, blank=True)
    executed_at: Any = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "agent_actions"
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(executed_at__isnull=True) | Q(confirmed_at__isnull=False),
                name="agent_actions_execution_requires_confirmation",
            ),
        ]
