from uuid import UUID

from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.assistant.api.mock_interview_serializers import (
    AnswerWriteSerializer,
    SessionReadSerializer,
    SessionWriteSerializer,
)
from backend.apps.assistant.models import MockInterviewSession
from backend.apps.assistant.services import mock_interviews as services
from backend.apps.assistant.services.interview_contracts import InterviewConflict, validate_key
from backend.apps.identity.api.common_permissions import active_request_user


class MockInterviewViewSet(GenericViewSet[MockInterviewSession]):
    queryset = MockInterviewSession.objects.none()
    serializer_class = SessionReadSerializer

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(services.list_sessions(active_request_user(request)))
        return self.get_paginated_response(SessionReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        return Response(
            SessionReadSerializer(services.get_session(active_request_user(request), pk)).data
        )

    def create(self, request: Request) -> Response:
        serializer = SessionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = services.create_session(
            active_request_user(request),
            key=request.headers.get("Idempotency-Key", ""),
            **serializer.validated_data,
        )
        return Response(SessionReadSerializer(session).data, status=202)

    @action(detail=True, methods=["post"])
    def start(self, request: Request, pk: UUID) -> Response:
        return Response(
            SessionReadSerializer(services.start_session(active_request_user(request), pk)).data
        )

    @action(detail=True, methods=["post"])
    def retry(self, request: Request, pk: UUID) -> Response:
        return Response(
            SessionReadSerializer(services.retry_session(active_request_user(request), pk)).data,
            status=202,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: UUID) -> Response:
        return Response(
            SessionReadSerializer(services.cancel_session(active_request_user(request), pk)).data
        )

    @action(detail=True, methods=["get"])
    def feedback(self, request: Request, pk: UUID) -> Response:
        session = services.get_session(active_request_user(request), pk)
        if session.status != "COMPLETED":
            raise InterviewConflict("Feedback is not ready.")
        return Response(session.feedback)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"turns/(?P<turn_id>[0-9a-f-]+)/answer",
        parser_classes=[MultiPartParser, FormParser],
    )
    def answer(self, request: Request, pk: UUID, turn_id: UUID) -> Response:
        serializer = AnswerWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = active_request_user(request)
        services.get_session(actor, pk)
        key = request.headers.get("Idempotency-Key", "")
        validate_key(key)
        from backend.apps.assistant.services.interview_media import submit_recording

        session = submit_recording(actor, pk, turn_id, key=key, **serializer.validated_data)
        return Response(SessionReadSerializer(session).data, status=202)

    @action(detail=True, methods=["get"], url_path=r"media/(?P<document_id>[0-9a-f-]+)")
    def media(self, request: Request, pk: UUID, document_id: UUID):
        from backend.apps.assistant.services.interview_media import stream_media

        return stream_media(active_request_user(request), pk, document_id)

    @action(detail=True, methods=["get"], url_path=r"avatars/(?P<key>[a-z0-9_]+)")
    def avatars(self, request: Request, pk: UUID, key: str):
        from backend.apps.assistant.services.interview_media import stream_avatar

        return stream_avatar(active_request_user(request), pk, key)
