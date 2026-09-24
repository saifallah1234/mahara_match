from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import IsActiveAuthenticated, active_request_user
from backend.apps.recruitment.api.application_status_history_serializers import (
    ApplicationStatusHistoryReadSerializer,
)
from backend.apps.recruitment.api.query_params import optional_uuid_param
from backend.apps.recruitment.models import ApplicationStatusHistory
from backend.apps.recruitment.services import application_status_history as history_services


class ApplicationStatusHistoryViewSet(GenericViewSet[ApplicationStatusHistory]):
    """Read-only, append-only history: entries cannot be overwritten through the API."""

    serializer_class = ApplicationStatusHistoryReadSerializer
    queryset = ApplicationStatusHistory.objects.none()
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(responses=ApplicationStatusHistoryReadSerializer(many=True))
    def list(self, request: Request) -> Response:
        queryset = history_services.list_status_history(
            active_request_user(request),
            application_id=optional_uuid_param(request, "application_id"),
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            ApplicationStatusHistoryReadSerializer(page, many=True).data
        )

    def retrieve(self, request: Request, pk: UUID) -> Response:
        entry = history_services.get_status_history_entry(active_request_user(request), pk)
        return Response(ApplicationStatusHistoryReadSerializer(entry).data)
