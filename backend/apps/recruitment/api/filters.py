from rest_framework import serializers

from backend.apps.candidates.models import WorkMode
from backend.apps.recruitment.models import ApplicationStatus, JobOfferStatus
from backend.common.api.filtering import QueryFilters


class JobOfferFilters(QueryFilters):
    status = serializers.ChoiceField(choices=JobOfferStatus.choices, required=False)
    governorate = serializers.CharField(
        source="governorate__iexact", max_length=100, required=False
    )
    city = serializers.CharField(source="city__iexact", max_length=100, required=False)
    work_mode = serializers.ChoiceField(choices=WorkMode.choices, required=False)
    organization_id = serializers.UUIDField(required=False)
    search = serializers.CharField(max_length=200, required=False)
    ordering = serializers.ChoiceField(
        choices=("created_at", "-created_at", "published_at", "-published_at", "title", "-title"),
        required=False,
    )
    search_fields = ("title", "description")


class ApplicationFilters(QueryFilters):
    offer_id = serializers.UUIDField(required=False)
    candidate_id = serializers.UUIDField(required=False)
    organization_id = serializers.UUIDField(source="offer__organization_id", required=False)
    status = serializers.ChoiceField(choices=ApplicationStatus.choices, required=False)
