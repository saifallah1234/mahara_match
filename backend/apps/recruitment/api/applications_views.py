from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import IsActiveAuthenticated, active_request_user
from backend.apps.recruitment.api.applications_serializers import ApplicationReadSerializer
from backend.apps.recruitment.models import Application
from backend.apps.recruitment.services import applications as application_services


class ApplicationViewSet(GenericViewSet[Application]):
    """Read-only: no create, update or delete operations exist in Phase 1."""

    serializer_class = ApplicationReadSerializer
    queryset = Application.objects.none()
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(responses=ApplicationReadSerializer(many=True))
    def list(self, request: Request) -> Response:
        queryset = application_services.list_applications(active_request_user(request))
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(ApplicationReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        application = application_services.get_application(active_request_user(request), pk)
        return Response(ApplicationReadSerializer(application).data)
