from typing import Any

from rest_framework import serializers

from backend.apps.training.models import DeliveryMode, ProgramLevel, ProgramStatus, TrainingProgram


class TrainingProgramReadSerializer(serializers.ModelSerializer[TrainingProgram]):
    class Meta:
        model = TrainingProgram
        fields = (
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
        )
        read_only_fields = fields


class TrainingProgramCreateSerializer(serializers.Serializer[dict[str, Any]]):
    organization_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    level = serializers.ChoiceField(choices=ProgramLevel.choices, required=False)
    delivery_mode = serializers.ChoiceField(choices=DeliveryMode.choices, required=False)
    status = serializers.ChoiceField(choices=ProgramStatus.choices, required=False)
    is_paid = serializers.BooleanField(required=False, default=False)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("is_paid") and not attrs.get("price"):
            raise serializers.ValidationError({"price": "A price is required for a paid program."})
        return attrs


class TrainingProgramUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    level = serializers.ChoiceField(choices=ProgramLevel.choices, required=False)
    delivery_mode = serializers.ChoiceField(choices=DeliveryMode.choices, required=False)
    status = serializers.ChoiceField(choices=ProgramStatus.choices, required=False)
    is_paid = serializers.BooleanField(required=False)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
