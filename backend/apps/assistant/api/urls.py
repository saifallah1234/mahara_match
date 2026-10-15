from django.urls import path
from rest_framework.routers import DefaultRouter

from backend.apps.assistant.api.agent_run_views import AgentRunView
from backend.apps.assistant.api.mock_interview_views import MockInterviewViewSet
from backend.apps.assistant.api.views import (
    ActionViewSet,
    ConversationViewSet,
    ExecutionViewSet,
    MessageViewSet,
    ToolCallViewSet,
)

router = DefaultRouter()
router.register("mock-interviews", MockInterviewViewSet, basename="mock-interview")
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("agent-executions", ExecutionViewSet, basename="agent-execution")

urlpatterns = [
    *router.urls,
    path("agent-runs/", AgentRunView.as_view(), name="agent-run"),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        MessageViewSet.as_view({"get": "list"}),
        name="conversation-message-list",
    ),
    path(
        "agent-executions/<uuid:execution_id>/tool-calls/",
        ToolCallViewSet.as_view({"get": "list"}),
        name="agent-tool-call-list",
    ),
    path(
        "agent-executions/<uuid:execution_id>/actions/",
        ActionViewSet.as_view({"get": "list"}),
        name="agent-action-list",
    ),
]
