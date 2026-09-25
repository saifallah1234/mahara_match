from typing import Any

from rest_framework import serializers

from backend.apps.identity.models import Organization, OrganizationType


class OrganizationReadSerializer(serializers.ModelSerializer[Organization]):
    parent_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = Organization
        fields = (
            "id",
            "parent_id",
            "type",
            "legal_name",
            "registration_number",
            "description",
            "website_url",
            "logo_uri",
            "matricule_fiscal",
            "governorate",
            "city",
            "address_line",
            "verification_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OrganizationCreateSerializer(serializers.Serializer[dict[str, Any]]):
    parent_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    type = serializers.ChoiceField(choices=OrganizationType.choices)
    legal_name = serializers.CharField(max_length=255)
    registration_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    description = serializers.CharField(required=False, allow_blank=True)
    website_url = serializers.CharField(required=False, allow_blank=True)
    logo_uri = serializers.CharField(required=False, allow_blank=True)
    matricule_fiscal = serializers.RegexField(
        regex=r"^\d{7}[A-Z]\d{3}\d{2}$",
        max_length=13,
        error_messages={"invalid": "Enter a valid 13-character Tunisian matricule fiscal."},
    )
    governorate = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    address_line = serializers.CharField(max_length=255, required=False, allow_blank=True)


class OrganizationUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    type = serializers.ChoiceField(
        choices=OrganizationType.choices,
        required=False,
    )
    legal_name = serializers.CharField(max_length=255, required=False)
    registration_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    description = serializers.CharField(required=False, allow_blank=True)
    website_url = serializers.CharField(required=False, allow_blank=True)
    logo_uri = serializers.CharField(required=False, allow_blank=True)
    matricule_fiscal = serializers.RegexField(
        regex=r"^\d{7}[A-Z]\d{3}\d{2}$",
        max_length=13,
        required=False,
        error_messages={"invalid": "Enter a valid 13-character Tunisian matricule fiscal."},
    )
    governorate = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    address_line = serializers.CharField(max_length=255, required=False, allow_blank=True)
