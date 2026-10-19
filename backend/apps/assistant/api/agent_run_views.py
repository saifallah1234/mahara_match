from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.agents.service import start_agent_run
from backend.apps.assistant.api.agent_run_serializers import (
    AgentRunErrorSerializer,
    AgentRunReadSerializer,
    AgentRunWriteSerializer,
)
from backend.apps.assistant.services.agent_access import agent_role
from backend.apps.identity.api.common_permissions import IsActiveAuthenticated, active_request_user


class AgentRunView(APIView):
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(
        request=AgentRunWriteSerializer,
        responses={200: AgentRunReadSerializer, 503: AgentRunErrorSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = AgentRunWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = active_request_user(request)
        role = agent_role(actor)
        result = start_agent_run(
            actor,
            serializer.validated_data["message"],
            serializer.validated_data.get("conversation_id"),
            role=role,
        )
        if result["error_code"]:
            return Response(
                {
                    "error": {
                        "code": result["error_code"],
                        "message": "The agent run could not be completed.",
                        "details": result,
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(result)
