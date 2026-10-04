from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.agents.service import start_agent_run
from backend.apps.assistant.api.agent_run_serializers import AgentRunWriteSerializer
from backend.apps.candidates.services.records import own_profile
from backend.apps.identity.api.common_permissions import IsActiveAuthenticated, active_request_user


class AgentRunView(APIView):
    permission_classes = (IsActiveAuthenticated,)

    def post(self, request: Request) -> Response:
        serializer = AgentRunWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = active_request_user(request)
        own_profile(actor)
        result = start_agent_run(
            actor,
            serializer.validated_data["message"],
            serializer.validated_data.get("conversation_id"),
        )
        if result["error_code"]:
            return Response(
                {"error": result["error_code"], **result},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(result)
