from decimal import Decimal
from typing import Any, cast

from rest_framework import serializers

from backend.apps.training.models import DeliveryMode, ProgramLevel, ProgramStatus, TrainingProgram


class TrainingProgramReadSerializer(serializers.ModelSerializer[TrainingProgram]):
    organization_id = serializers.UUIDField(read_only=True)
    organization_name = serializers.CharField(source="organization.legal_name", read_only=True)

    class Meta:
        model = TrainingProgram
        fields = (
            "id",
            "organization_id",
            "organization_name",
            "title",
            "description",
            "level",
            "delivery_mode",
            "status",
            "is_free",
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
    is_free = serializers.BooleanField(required=False, default=True)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=Decimal("0")
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if (attrs["is_free"] and attrs["price"] != 0) or (
            not attrs["is_free"] and attrs["price"] <= 0
        ):
            raise serializers.ValidationError(
                {"price": "Free programs cost 0 TND; paid programs cost more than 0 TND."}
            )
        return attrs


class TrainingProgramUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    level = serializers.ChoiceField(choices=ProgramLevel.choices, required=False)
    delivery_mode = serializers.ChoiceField(choices=DeliveryMode.choices, required=False)
    status = serializers.ChoiceField(choices=ProgramStatus.choices, required=False)
    is_free = serializers.BooleanField(required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        program = cast(TrainingProgram, self.instance)
        is_free = attrs.get("is_free", program.is_free)
        price = attrs.get("price", program.price)
        if (is_free and price != 0) or (not is_free and price <= 0):
            raise serializers.ValidationError(
                {"price": "Free programs cost 0 TND; paid programs cost more than 0 TND."}
            )
        return attrs
