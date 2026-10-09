from typing import Any, cast
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.identity.services.access import require_permission
from backend.apps.training.api.filters import ProgramFilters
from backend.apps.training.api.programs_serializers import (
    TrainingProgramCreateSerializer,
    TrainingProgramReadSerializer,
    TrainingProgramUpdateSerializer,
)
from backend.apps.training.models import TrainingProgram
from backend.apps.training.services import programs as program_services
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.api.query_params import uuid_query_param


class TrainingProgramViewSet(GenericViewSet[TrainingProgram]):
    serializer_class = TrainingProgramReadSerializer
    queryset = TrainingProgram.objects.none()

    @extend_schema(
        parameters=[OpenApiParameter("organization_id", UUID, required=False), ProgramFilters],
        responses=TrainingProgramReadSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        require_permission(active_request_user(request), TrainingPermissionCode.VIEW_CATALOG)
        queryset = program_services.list_programs(
            active_request_user(request),
            organization_id=uuid_query_param(request, "organization_id"),
        )
        queryset = (
            ProgramFilters(data=request.query_params).apply(queryset).select_related("organization")
        )
        queryset = queryset.order_by("-created_at", "id")
        page = self.paginate_queryset(queryset)
        serializer = TrainingProgramReadSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        request=TrainingProgramCreateSerializer,
        responses={201: TrainingProgramReadSerializer},
    )
    def create(self, request: Request) -> Response:
        serializer = TrainingProgramCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        program = program_services.create_program(
            active_request_user(request), serializer.validated_data
        )
        return Response(TrainingProgramReadSerializer(program).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        program = program_services.get_program(active_request_user(request), pk)
        return Response(TrainingProgramReadSerializer(program).data)

    @extend_schema(request=TrainingProgramUpdateSerializer, responses=TrainingProgramReadSerializer)
    def update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=False)

    @extend_schema(request=TrainingProgramUpdateSerializer, responses=TrainingProgramReadSerializer)
    def partial_update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=True)

    def _update(self, request: Request, pk: UUID, *, partial: bool) -> Response:
        actor = active_request_user(request)
        program = program_services.get_program(actor, pk)
        serializer = TrainingProgramUpdateSerializer(
            cast(Any, program), data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        program = program_services.update_program(actor, program, serializer.validated_data)
        return Response(TrainingProgramReadSerializer(program).data)

    def destroy(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        program = program_services.get_program(actor, pk)
        program_services.delete_program(actor, program)
        return Response(status=status.HTTP_204_NO_CONTENT)
