from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.identity.services.access import has_permission, require_permission
from backend.apps.identity.services.organization_members import member_organization_ids
from backend.apps.training.api.enrollments_serializers import (
    TrainingEnrollmentCreateSerializer,
    TrainingEnrollmentProgressSerializer,
    TrainingEnrollmentReadSerializer,
    TrainingEnrollmentReceiverReadSerializer,
)
from backend.apps.training.api.filters import EnrollmentFilters
from backend.apps.training.models import TrainingEnrollment
from backend.apps.training.services import enrollments as enrollment_services
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.api.query_params import uuid_query_param


def _read(enrollment: TrainingEnrollment, member_org_ids: set[UUID]) -> dict[str, object]:
    if enrollment.session.program.organization_id in member_org_ids:
        return dict(TrainingEnrollmentReceiverReadSerializer(enrollment).data)
    return dict(TrainingEnrollmentReadSerializer(enrollment).data)


class TrainingEnrollmentViewSet(GenericViewSet[TrainingEnrollment]):
    serializer_class = TrainingEnrollmentReadSerializer
    queryset = TrainingEnrollment.objects.none()

    @extend_schema(
        parameters=[
            EnrollmentFilters,
            OpenApiParameter("organization_id", UUID, required=False),
        ],
        responses=TrainingEnrollmentReadSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        actor = active_request_user(request)
        if not has_permission(actor, TrainingPermissionCode.VIEW_OWN_ENROLLMENTS):
            require_permission(actor, TrainingPermissionCode.MANAGE_ENROLLMENTS)
        queryset = enrollment_services.list_enrollments(
            actor,
            organization_id=uuid_query_param(request, "organization_id"),
        ).select_related("candidate__user", "session__program")
        queryset = EnrollmentFilters(data=request.query_params).apply(queryset)
        queryset = queryset.order_by("enrolled_at", "id")
        page = self.paginate_queryset(queryset)
        member_org_ids = member_organization_ids(actor)
        return self.get_paginated_response([_read(row, member_org_ids) for row in page or []])

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
            _read(enrollment, member_organization_ids(active_request_user(request))),
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        enrollment = enrollment_services.get_enrollment(actor, pk)
        return Response(_read(enrollment, member_organization_ids(actor)))

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
        return Response(_read(enrollment, member_organization_ids(actor)))

    def destroy(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        enrollment = enrollment_services.get_enrollment(actor, pk)
        enrollment_services.cancel_enrollment(actor, enrollment)
        return Response(status=status.HTTP_204_NO_CONTENT)
