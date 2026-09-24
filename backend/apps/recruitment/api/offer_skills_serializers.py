from typing import Any

from rest_framework import serializers

from backend.apps.recruitment.models import OfferSkill


class OfferSkillReadSerializer(serializers.ModelSerializer[OfferSkill]):
    offer_id = serializers.UUIDField(read_only=True)
    skill_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = OfferSkill
        fields = (
            "id",
            "offer_id",
            "skill_id",
            "importance",
            "required_level",
            "is_mandatory",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OfferSkillUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    # G04/Q20: level and importance scales are undefined, so these stay free text.
    importance = serializers.CharField(max_length=30, required=False, allow_blank=True)
    required_level = serializers.CharField(max_length=30, required=False, allow_blank=True)
    is_mandatory = serializers.BooleanField(required=False)


class OfferSkillCreateSerializer(OfferSkillUpdateSerializer):
    offer_id = serializers.UUIDField()
    skill_id = serializers.UUIDField()
