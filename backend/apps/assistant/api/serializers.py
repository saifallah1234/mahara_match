from typing import Any

from rest_framework import serializers

from backend.apps.assistant.models import (
    AgentAction,
    AgentExecution,
    AgentToolCall,
    Conversation,
    ConversationMessage,
)


class ConversationReadSerializer(serializers.ModelSerializer[Conversation]):
    class Meta:
        model = Conversation
        fields = ("id", "title", "status", "started_at", "last_message_at", "created_at")
        read_only_fields = fields


class ConversationWriteSerializer(serializers.Serializer[dict[str, Any]]):
    title = serializers.CharField(max_length=200, allow_blank=True, required=False)


class MessageReadSerializer(serializers.ModelSerializer[ConversationMessage]):
    class Meta:
        model = ConversationMessage
        fields = (
            "id",
            "conversation_id",
            "sender_type",
            "content",
            "intent",
            "citations_json",
            "created_at",
        )
        read_only_fields = fields


class ExecutionReadSerializer(serializers.ModelSerializer[AgentExecution]):
    class Meta:
        model = AgentExecution
        fields = (
            "id",
            "request_message_id",
            "response_message_id",
            "route",
            "status",
            "agent_version",
            "latency_ms",
            "error_code",
            "created_at",
        )
        read_only_fields = fields


class ToolCallReadSerializer(serializers.ModelSerializer[AgentToolCall]):
    class Meta:
        model = AgentToolCall
        fields = (
            "id",
            "execution_id",
            "tool_name",
            "status",
            "latency_ms",
            "error_code",
            "created_at",
        )
        read_only_fields = fields


class ActionReadSerializer(serializers.ModelSerializer[AgentAction]):
    class Meta:
        model = AgentAction
        fields = (
            "id",
            "execution_id",
            "action_type",
            "target_type",
            "target_id",
            "status",
            "confirmed_at",
            "executed_at",
            "created_at",
        )
        read_only_fields = fields
