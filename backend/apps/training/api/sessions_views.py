from typing import Any, cast
from uuid import UUID

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.training.api.sessions_serializers import (
    TrainingSessionCreateSerializer,
    TrainingSessionReadSerializer,
    TrainingSessionUpdateSerializer,
)
from backend.apps.training.models import TrainingSession
from backend.apps.training.services import sessions as session_services
from backend.common.exceptions import DomainValidationError


class TrainingSessionViewSet(GenericViewSet[TrainingSession]):
    serializer_class = TrainingSessionReadSerializer
    queryset = TrainingSession.objects.none()

    def list(self, request: Request) -> Response:
        program_id = request.query_params.get("program_id")
        if not program_id:
            raise DomainValidationError(
                details={"program_id": ["This query parameter is required."]}
            )
        queryset = session_services.list_program_sessions(active_request_user(request), program_id)
        page = self.paginate_queryset(queryset)
        serializer = TrainingSessionReadSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def create(self, request: Request) -> Response:
        serializer = TrainingSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = session_services.create_session(
            active_request_user(request), serializer.validated_data
        )
        return Response(TrainingSessionReadSerializer(session).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        session = session_services.get_session(active_request_user(request), pk)
        return Response(TrainingSessionReadSerializer(session).data)

    def update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=False)

    def partial_update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=True)

    def _update(self, request: Request, pk: UUID, *, partial: bool) -> Response:
        actor = active_request_user(request)
        session = session_services.get_session(actor, pk)
        serializer = TrainingSessionUpdateSerializer(
            cast(Any, session), data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        session = session_services.update_session(actor, session, serializer.validated_data)
        return Response(TrainingSessionReadSerializer(session).data)

    def destroy(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        session = session_services.get_session(actor, pk)
        session_services.delete_session(actor, session)
        return Response(status=status.HTTP_204_NO_CONTENT)
