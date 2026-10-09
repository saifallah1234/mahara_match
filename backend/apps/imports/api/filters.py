from rest_framework import serializers

from backend.common.api.filtering import QueryFilters


class BatchFilters(QueryFilters):
    source_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=("STARTED", "COMPLETED", "FAILED"), required=False)
    started_after = serializers.DateTimeField(source="started_at__gte", required=False)
    started_before = serializers.DateTimeField(source="started_at__lte", required=False)
    completed_after = serializers.DateTimeField(source="completed_at__gte", required=False)
    completed_before = serializers.DateTimeField(source="completed_at__lte", required=False)


class RowFilters(QueryFilters):
    status = serializers.ChoiceField(
        choices=("ADDED", "UPDATED", "UNCHANGED", "REJECTED"), required=False
    )
    source_id = serializers.UUIDField(source="batch__source_id", required=False)
    created_after = serializers.DateTimeField(source="created_at__gte", required=False)
    created_before = serializers.DateTimeField(source="created_at__lte", required=False)
