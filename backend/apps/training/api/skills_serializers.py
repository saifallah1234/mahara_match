from rest_framework import serializers

from backend.apps.training.models import TrainingSkill


class TrainingSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSkill
        fields = ["id", "program", "skill_id", "target_level", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
