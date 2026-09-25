from typing import Any

from rest_framework import serializers

from backend.apps.training.models import SessionStatus, TrainingSession


class TrainingSessionReadSerializer(serializers.ModelSerializer[TrainingSession]):
    class Meta:
        model = TrainingSession
        fields = (
            "id",
            "program",
            "start_date",
            "end_date",
            "capacity",
            "location_or_url",
            "registration_deadline",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TrainingSessionCreateSerializer(serializers.Serializer[dict[str, Any]]):
    program_id = serializers.UUIDField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    capacity = serializers.IntegerField(min_value=1)
    location_or_url = serializers.CharField(max_length=500)
    registration_deadline = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=SessionStatus.choices, required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["end_date"] <= attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "Must be after the start date."})
        if attrs["registration_deadline"] > attrs["start_date"]:
            raise serializers.ValidationError(
                {"registration_deadline": "Must be on or before the start date."}
            )
        return attrs


class TrainingSessionUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    capacity = serializers.IntegerField(min_value=1, required=False)
    location_or_url = serializers.CharField(max_length=500, required=False)
    registration_deadline = serializers.DateTimeField(required=False)
    status = serializers.ChoiceField(choices=SessionStatus.choices, required=False)
