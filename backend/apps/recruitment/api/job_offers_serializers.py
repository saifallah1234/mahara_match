from typing import Any

from rest_framework import serializers

from backend.apps.recruitment.models import JobOffer


class JobOfferReadSerializer(serializers.ModelSerializer[JobOffer]):
    organization_id = serializers.UUIDField(read_only=True)
    created_by_id = serializers.UUIDField(read_only=True)
    source_id = serializers.UUIDField(read_only=True, allow_null=True)
    description_language_id = serializers.UUIDField(read_only=True, allow_null=True)
    required_language_id = serializers.UUIDField(read_only=True, allow_null=True)
    education_level_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = JobOffer
        fields = (
            "id",
            "organization_id",
            "created_by_id",
            "source_id",
            "external_id",
            "title",
            "description",
            "contract_type",
            "work_mode",
            "experience_level",
            "country_code",
            "governorate",
            "city",
            "min_salary",
            "max_salary",
            "application_deadline",
            "status",
            "published_at",
            "closed_at",
            "offer_url",
            "description_language_id",
            "required_language_id",
            "education_level_id",
            "easy_apply",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class _JobOfferWriteSerializer(serializers.Serializer[dict[str, Any]]):
    """Whitelist of caller-editable fields. Salaries wait for Q10 (currency)."""

    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    contract_type = serializers.CharField(max_length=30, required=False, allow_blank=True)
    work_mode = serializers.CharField(max_length=30, required=False, allow_blank=True)
    experience_level = serializers.CharField(max_length=30, required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True)
    governorate = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    application_deadline = serializers.DateField(required=False, allow_null=True)
    offer_url = serializers.CharField(max_length=50, required=False, allow_blank=True)
    description_language_id = serializers.UUIDField(required=False, allow_null=True)
    required_language_id = serializers.UUIDField(required=False, allow_null=True)
    education_level_id = serializers.UUIDField(required=False, allow_null=True)
    easy_apply = serializers.BooleanField()


class JobOfferCreateSerializer(_JobOfferWriteSerializer):
    organization_id = serializers.UUIDField()


class JobOfferUpdateSerializer(_JobOfferWriteSerializer):
    """The owning organization cannot be changed after creation."""
