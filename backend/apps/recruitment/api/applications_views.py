from io import BytesIO
from uuid import UUID

from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import IsActiveAuthenticated, active_request_user
from backend.apps.recruitment.api.applications_serializers import (
    ApplicationReadSerializer,
    ApplicationSubmitSerializer,
    ApplicationTransitionSerializer,
)
from backend.apps.recruitment.api.filters import ApplicationFilters
from backend.apps.recruitment.models import Application
from backend.apps.recruitment.services import applications as application_services
from backend.apps.recruitment.services.application_lifecycle import (
    submit_application,
    transition_application,
)


class ApplicationViewSet(GenericViewSet[Application]):
    """Application submission and controlled state changes."""

    serializer_class = ApplicationReadSerializer
    queryset = Application.objects.none()
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(parameters=[ApplicationFilters], responses=ApplicationReadSerializer(many=True))
    def list(self, request: Request) -> Response:
        queryset = application_services.list_applications(
            active_request_user(request)
        ).select_related("offer", "candidate__user")
        queryset = ApplicationFilters(data=request.query_params).apply(queryset)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(ApplicationReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        application = application_services.get_application(active_request_user(request), pk)
        return Response(ApplicationReadSerializer(application).data)

    @extend_schema(
        description="Download the exact active CV version submitted with this application.",
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
    )
    @action(detail=True, methods=("get",), url_path="cv")
    def cv(self, request: Request, pk: UUID) -> FileResponse:
        document, content = application_services.download_application_cv(
            active_request_user(request), pk
        )
        response = FileResponse(
            BytesIO(content),
            as_attachment=True,
            filename=document.file_name,
            content_type=document.mime_type,
        )
        response["Content-Length"] = str(document.size_bytes)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @extend_schema(request=ApplicationSubmitSerializer, responses={201: ApplicationReadSerializer})
    def create(self, request: Request) -> Response:
        serializer = ApplicationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = submit_application(active_request_user(request), serializer.validated_data)
        return Response(ApplicationReadSerializer(application).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=ApplicationTransitionSerializer, responses=ApplicationReadSerializer)
    @action(detail=True, methods=["post"])
    def transition(self, request: Request, pk: UUID) -> Response:
        serializer = ApplicationTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = transition_application(
            active_request_user(request),
            pk,
            serializer.validated_data["status"],
            serializer.validated_data.get("reason", ""),
        )
        return Response(ApplicationReadSerializer(application).data)
