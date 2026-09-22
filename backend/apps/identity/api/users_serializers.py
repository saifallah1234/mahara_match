from typing import Any

from rest_framework import serializers

from backend.apps.identity.models import User
from backend.apps.identity.services.users import role_assignment_summaries


class UserReadSerializer(serializers.ModelSerializer[User]):
    role_assignments = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "status",
            "email_verified_at",
            "last_login",
            "created_at",
            "updated_at",
            "role_assignments",
        )
        read_only_fields = fields

    def get_role_assignments(self, user: User) -> list[dict[str, Any]]:
        return role_assignment_summaries(user)


class UserCreateSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)


class UserProfileUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
