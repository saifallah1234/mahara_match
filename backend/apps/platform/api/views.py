from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.platform.api.filters import AuditFilters
from backend.apps.platform.api.serializers import AuditReadSerializer, NotificationReadSerializer
from backend.apps.platform.models import AuditLog, Notification
from backend.apps.platform.services import records


class NotificationViewSet(GenericViewSet[Notification]):
    serializer_class = NotificationReadSerializer
    queryset = Notification.objects.none()

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(records.list_notifications(active_request_user(request)))
        return self.get_paginated_response(NotificationReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        return Response(
            NotificationReadSerializer(
                records.get_notification(active_request_user(request), pk)
            ).data
        )

    @extend_schema(request=None, responses=NotificationReadSerializer)
    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request: Request, pk: UUID) -> Response:
        return Response(
            NotificationReadSerializer(records.mark_read(active_request_user(request), pk)).data
        )


class AuditViewSet(GenericViewSet[AuditLog]):
    serializer_class = AuditReadSerializer
    queryset = AuditLog.objects.none()

    @extend_schema(parameters=[AuditFilters], responses=AuditReadSerializer(many=True))
    def list(self, request: Request) -> Response:
        queryset = records.list_audit_logs(active_request_user(request))
        queryset = AuditFilters(data=request.query_params).apply(queryset)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(AuditReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        return Response(
            AuditReadSerializer(records.get_audit_log(active_request_user(request), pk)).data
        )
