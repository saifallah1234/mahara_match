from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.training.api.enrollments_serializers import (
    TrainingEnrollmentCreateSerializer,
    TrainingEnrollmentProgressSerializer,
    TrainingEnrollmentReadSerializer,
)
from backend.apps.training.models import TrainingEnrollment
from backend.apps.training.services import enrollments as enrollment_services
from backend.common.api.query_params import uuid_query_param


class TrainingEnrollmentViewSet(GenericViewSet[TrainingEnrollment]):
    serializer_class = TrainingEnrollmentReadSerializer
    queryset = TrainingEnrollment.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter("candidate_id", UUID, required=False),
            OpenApiParameter("organization_id", UUID, required=False),
        ],
        responses=TrainingEnrollmentReadSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        queryset = enrollment_services.list_enrollments(
            active_request_user(request),
            candidate_id=uuid_query_param(request, "candidate_id"),
            organization_id=uuid_query_param(request, "organization_id"),
        )
        page = self.paginate_queryset(queryset)
        serializer = TrainingEnrollmentReadSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        request=TrainingEnrollmentCreateSerializer,
        responses={201: TrainingEnrollmentReadSerializer},
    )
    def create(self, request: Request) -> Response:
        serializer = TrainingEnrollmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = enrollment_services.enroll_candidate(
            active_request_user(request), serializer.validated_data
        )
        return Response(
            TrainingEnrollmentReadSerializer(enrollment).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request: Request, pk: UUID) -> Response:
        enrollment = enrollment_services.get_enrollment(active_request_user(request), pk)
        return Response(TrainingEnrollmentReadSerializer(enrollment).data)

    @extend_schema(
        request=TrainingEnrollmentProgressSerializer,
        responses=TrainingEnrollmentReadSerializer,
    )
    @action(detail=True, methods=("patch",), url_path="progress")
    def progress(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        enrollment = enrollment_services.get_enrollment(actor, pk)
        serializer = TrainingEnrollmentProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = enrollment_services.update_progress(
            actor, enrollment, serializer.validated_data["completion_rate"]
        )
        return Response(TrainingEnrollmentReadSerializer(enrollment).data)

    def destroy(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        enrollment = enrollment_services.get_enrollment(actor, pk)
        enrollment_services.cancel_enrollment(actor, enrollment)
        return Response(status=status.HTTP_204_NO_CONTENT)
