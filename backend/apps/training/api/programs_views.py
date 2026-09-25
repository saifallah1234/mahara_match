from uuid import UUID

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.training.api.programs_serializers import (
    TrainingProgramCreateSerializer,
    TrainingProgramReadSerializer,
    TrainingProgramUpdateSerializer,
)
from backend.apps.training.models import TrainingProgram
from backend.apps.training.services import programs as program_services


class TrainingProgramViewSet(GenericViewSet[TrainingProgram]):
    serializer_class = TrainingProgramReadSerializer
    queryset = TrainingProgram.objects.none()

    def list(self, request: Request) -> Response:
        queryset = program_services.list_programs(
            active_request_user(request),
            organization_id=request.query_params.get("organization_id"),
        )
        page = self.paginate_queryset(queryset)
        serializer = TrainingProgramReadSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

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

    def update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=False)

    def partial_update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=True)

    def _update(self, request: Request, pk: UUID, *, partial: bool) -> Response:
        actor = active_request_user(request)
        program = program_services.get_program(actor, pk)
        serializer = TrainingProgramUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        program = program_services.update_program(actor, program, serializer.validated_data)
        return Response(TrainingProgramReadSerializer(program).data)

    def destroy(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        program = program_services.get_program(actor, pk)
        program_services.delete_program(actor, program)
        return Response(status=status.HTTP_204_NO_CONTENT)
