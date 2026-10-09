from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.assistant.api.serializers import (
    ActionReadSerializer,
    ConversationReadSerializer,
    ConversationWriteSerializer,
    ExecutionReadSerializer,
    MessageReadSerializer,
    ToolCallReadSerializer,
)
from backend.apps.assistant.models import AgentExecution, Conversation
from backend.apps.assistant.services import records
from backend.apps.identity.api.common_permissions import active_request_user


class ConversationViewSet(GenericViewSet[Conversation]):
    serializer_class = ConversationReadSerializer
    queryset = Conversation.objects.none()

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(records.list_conversations(active_request_user(request)))
        return self.get_paginated_response(ConversationReadSerializer(page, many=True).data)

    @extend_schema(request=ConversationWriteSerializer, responses={201: ConversationReadSerializer})
    def create(self, request: Request) -> Response:
        serializer = ConversationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = records.create_conversation(
            active_request_user(request), serializer.validated_data.get("title", "")
        )
        return Response(
            ConversationReadSerializer(conversation).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request: Request, pk: UUID) -> Response:
        return Response(
            ConversationReadSerializer(
                records.get_conversation(active_request_user(request), pk)
            ).data
        )

    @extend_schema(request=ConversationWriteSerializer, responses=ConversationReadSerializer)
    def partial_update(self, request: Request, pk: UUID) -> Response:
        serializer = ConversationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if "title" not in serializer.validated_data:
            raise ValidationError({"title": ["Required."]})
        conversation = records.rename_conversation(
            active_request_user(request), pk, serializer.validated_data["title"]
        )
        return Response(ConversationReadSerializer(conversation).data)

    def destroy(self, request: Request, pk: UUID) -> Response:
        records.delete_conversation(active_request_user(request), pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageViewSet(GenericViewSet):
    serializer_class = MessageReadSerializer

    def list(self, request: Request, conversation_id: UUID) -> Response:
        page = self.paginate_queryset(
            records.list_messages(active_request_user(request), conversation_id)
        )
        return self.get_paginated_response(MessageReadSerializer(page, many=True).data)


class ExecutionViewSet(GenericViewSet):
    serializer_class = ExecutionReadSerializer
    queryset = AgentExecution.objects.none()

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(records.list_executions(active_request_user(request)))
        return self.get_paginated_response(ExecutionReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        execution = records.get_execution(active_request_user(request), pk)
        return Response(ExecutionReadSerializer(execution).data)


class ToolCallViewSet(GenericViewSet):
    serializer_class = ToolCallReadSerializer

    def list(self, request: Request, execution_id: UUID) -> Response:
        page = self.paginate_queryset(
            records.list_tool_calls(active_request_user(request), execution_id)
        )
        return self.get_paginated_response(ToolCallReadSerializer(page, many=True).data)


class ActionViewSet(GenericViewSet):
    serializer_class = ActionReadSerializer

    def list(self, request: Request, execution_id: UUID) -> Response:
        page = self.paginate_queryset(
            records.list_actions(active_request_user(request), execution_id)
        )
        return self.get_paginated_response(ActionReadSerializer(page, many=True).data)
