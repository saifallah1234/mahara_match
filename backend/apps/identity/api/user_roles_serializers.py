from typing import Any

from rest_framework import serializers

from backend.apps.identity.models import UserRole


class UserRoleReadSerializer(serializers.ModelSerializer[UserRole]):
    user_id = serializers.UUIDField(read_only=True)
    role_id = serializers.UUIDField(read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)
    organization_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = UserRole
        fields = (
            "id",
            "user_id",
            "role_id",
            "role_code",
            "organization_id",
            "assigned_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class UserRoleCreateSerializer(serializers.Serializer[dict[str, Any]]):
    user_id = serializers.UUIDField()
    role_id = serializers.UUIDField()
    organization_id = serializers.UUIDField(required=False, allow_null=True, default=None)
