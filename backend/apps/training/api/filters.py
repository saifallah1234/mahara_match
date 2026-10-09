from rest_framework import serializers

from backend.apps.training.models import (
    DeliveryMode,
    EnrollmentStatus,
    ProgramStatus,
    SessionStatus,
)
from backend.common.api.filtering import QueryFilters


class ProgramFilters(QueryFilters):
    skill_id = serializers.UUIDField(source="program_skills__skill_id", required=False)
    governorate = serializers.CharField(
        source="organization__governorate__iexact", max_length=100, required=False
    )
    delivery_mode = serializers.ChoiceField(choices=DeliveryMode.choices, required=False)
    status = serializers.ChoiceField(choices=ProgramStatus.choices, required=False)


class SessionFilters(QueryFilters):
    organization_id = serializers.UUIDField(source="program__organization_id", required=False)
    skill_id = serializers.UUIDField(source="program__program_skills__skill_id", required=False)
    delivery_mode = serializers.ChoiceField(
        source="program__delivery_mode", choices=DeliveryMode.choices, required=False
    )
    location = serializers.CharField(
        source="location_or_url__icontains", max_length=500, required=False
    )
    status = serializers.ChoiceField(choices=SessionStatus.choices, required=False)
    starts_after = serializers.DateTimeField(source="start_date__gte", required=False)
    starts_before = serializers.DateTimeField(source="start_date__lte", required=False)
    ends_after = serializers.DateTimeField(source="end_date__gte", required=False)
    ends_before = serializers.DateTimeField(source="end_date__lte", required=False)


class EnrollmentFilters(QueryFilters):
    candidate_id = serializers.UUIDField(required=False)
    session_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=EnrollmentStatus.choices, required=False)
