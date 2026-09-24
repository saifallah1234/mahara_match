from rest_framework import serializers

from backend.apps.training.models import TrainingProgram


class TrainingProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingProgram
        fields = [
            "id",
            "organization_id",
            "title",
            "description",
            "level",
            "delivery_mode",
            "status",
            "is_paid",
            "price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
