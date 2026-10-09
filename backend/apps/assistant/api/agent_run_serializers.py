from typing import Any

from rest_framework import serializers


class AgentRunWriteSerializer(serializers.Serializer[dict[str, Any]]):
    message = serializers.CharField(max_length=4000, trim_whitespace=True)
    conversation_id = serializers.UUIDField(required=False)


class AgentRunReadSerializer(serializers.Serializer[dict[str, Any]]):
    conversation_id = serializers.UUIDField()
    execution_id = serializers.UUIDField()
    message_id = serializers.UUIDField(allow_null=True)
    reply = serializers.CharField(allow_null=True)
    error_code = serializers.CharField(allow_null=True)


class AgentRunErrorSerializer(serializers.Serializer[dict[str, Any]]):
    error = serializers.DictField()
