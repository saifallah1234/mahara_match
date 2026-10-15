from rest_framework import serializers

from backend.common.api.filtering import QueryFilters


class OfferMatchFilters(QueryFilters):
    offer_id = serializers.UUIDField(required=False)
    candidate_id = serializers.UUIDField(required=False)
    model_version = serializers.CharField(max_length=50, required=False)
    calculated_after = serializers.DateTimeField(source="calculated_at__gte", required=False)
    calculated_before = serializers.DateTimeField(source="calculated_at__lte", required=False)
