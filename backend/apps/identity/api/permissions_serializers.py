from typing import Any

from rest_framework import serializers

from backend.apps.identity.models import Permission


class PermissionReadSerializer(serializers.ModelSerializer[Permission]):
    class Meta:
        model = Permission
        fields = ("id", "code", "resource", "action", "created_at", "updated_at")
        read_only_fields = fields


class PermissionCreateSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField(max_length=150)
    resource = serializers.CharField(max_length=100)
    action = serializers.CharField(max_length=50)
