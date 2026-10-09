from rest_framework import serializers

from backend.common.api.filtering import QueryFilters


class AuditFilters(QueryFilters):
    actor_id = serializers.UUIDField(source="actor_user_id", required=False)
    action = serializers.CharField(max_length=100, required=False)
    entity_type = serializers.CharField(max_length=100, required=False)
    entity_id = serializers.UUIDField(required=False)
    created_after = serializers.DateTimeField(source="created_at__gte", required=False)
    created_before = serializers.DateTimeField(source="created_at__lte", required=False)
