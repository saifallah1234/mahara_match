from typing import Any

from rest_framework import serializers

from backend.apps.candidates.models.entities import SkillLevel
from backend.apps.training.models import TrainingSkill, TrainingSkillPurpose


class TrainingSkillReadSerializer(serializers.ModelSerializer[TrainingSkill]):
    class Meta:
        model = TrainingSkill
        fields = (
            "id",
            "program",
            "skill_id",
            "target_level",
            "purpose",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TrainingSkillCreateSerializer(serializers.Serializer[dict[str, Any]]):
    program_id = serializers.UUIDField()
    skill_id = serializers.UUIDField()
    target_level = serializers.ChoiceField(choices=SkillLevel.choices)
    purpose = serializers.ChoiceField(choices=TrainingSkillPurpose.choices, required=False)
