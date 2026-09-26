from typing import Any

from rest_framework import serializers

from backend.apps.identity.models import RolePermission


class RolePermissionReadSerializer(serializers.ModelSerializer[RolePermission]):
    role_id = serializers.UUIDField(read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)
    permission_id = serializers.UUIDField(read_only=True)
    permission_code = serializers.CharField(source="permission.code", read_only=True)

    class Meta:
        model = RolePermission
        fields = (
            "id",
            "role_id",
            "role_code",
            "permission_id",
            "permission_code",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RolePermissionCreateSerializer(serializers.Serializer[dict[str, Any]]):
    role_id = serializers.UUIDField()
    permission_id = serializers.UUIDField()
