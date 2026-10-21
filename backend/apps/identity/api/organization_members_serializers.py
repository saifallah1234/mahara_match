from typing import Any

from rest_framework import serializers

from backend.apps.identity.models import OrganizationMember, UserRole


class OrganizationMemberReadSerializer(serializers.ModelSerializer[OrganizationMember]):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMember
        fields = (
            "id",
            "organization",
            "user",
            "first_name",
            "last_name",
            "email",
            "role",
            "job_title",
            "joined_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_role(self, member: OrganizationMember) -> str | None:
        assignment = (
            UserRole.objects.filter(user_id=member.user_id, organization_id=member.organization_id)
            .select_related("role")
            .first()
        )
        return assignment.role.code if assignment else None


class OrganizationMemberCreateSerializer(serializers.Serializer[dict[str, Any]]):
    user = serializers.UUIDField()
    job_title = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    joined_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )


class OrganizationMemberUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    job_title = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    joined_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )
