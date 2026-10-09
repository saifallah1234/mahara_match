from typing import Any

from django.db.models import Model, Q, QuerySet
from rest_framework import serializers


class QueryFilters(serializers.Serializer[dict[str, Any]]):
    search_fields: tuple[str, ...] = ()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for lookup, start in attrs.items():
            if lookup.endswith("__gte"):
                end = attrs.get(lookup.removesuffix("__gte") + "__lte")
                if end is not None and end < start:
                    raise serializers.ValidationError("Date range end must be on or after start.")
        return attrs

    def apply[M: Model](self, queryset: QuerySet[M]) -> QuerySet[M]:
        """Narrow an already authorized queryset using declared query fields only."""
        self.is_valid(raise_exception=True)
        filters = dict(self.validated_data)
        ordering = filters.pop("ordering", None)
        search = filters.pop("search", None)
        queryset = queryset.filter(**filters)
        if search:
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{f"{field}__icontains": search})
            queryset = queryset.filter(condition)
        if ordering:
            queryset = queryset.order_by(ordering, "id")
        return queryset.distinct()
