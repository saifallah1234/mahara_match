from typing import Any

from rest_framework import serializers

from backend.apps.identity.models import Role


class RoleReadSerializer(serializers.ModelSerializer[Role]):
    class Meta:
        model = Role
        fields = ("id", "code", "name", "description", "created_at", "updated_at")
        read_only_fields = fields


class RoleUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
