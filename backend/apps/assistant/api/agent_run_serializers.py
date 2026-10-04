from typing import Any

from rest_framework import serializers


class AgentRunWriteSerializer(serializers.Serializer[dict[str, Any]]):
    message = serializers.CharField(max_length=4000, trim_whitespace=True)
    conversation_id = serializers.UUIDField(required=False)
