from typing import Any

from rest_framework import serializers

from backend.apps.identity.models import OrganizationMember


class OrganizationMemberReadSerializer(serializers.ModelSerializer[OrganizationMember]):
    class Meta:
        model = OrganizationMember
        fields = (
            "organization",
            "user",
            "job_title",
            "joined_at",
        )
        read_only_fields = fields


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
