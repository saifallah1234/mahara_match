from __future__ import annotations

from time import monotonic
from typing import TYPE_CHECKING, Any
from uuid import UUID

from ai.agents.anetai import (
    AGENT_VERSION,
    ROUTE,
    UNSUPPORTED_ROUTE,
    is_job_match_request,
    run_job_matching_agent,
)
from backend.apps.assistant.services.records import (
    create_conversation,
    get_conversation,
    record_execution,
    record_message,
    record_tool_call,
)

if TYPE_CHECKING:
    from backend.apps.assistant.models import Conversation
    from backend.apps.identity.models import User


def start_agent_run(
    actor: User, prompt: str, conversation_id: UUID | str | None = None
) -> dict[str, Any]:
    conversation: Conversation
    if conversation_id is None:
        conversation = create_conversation(actor, "Job matches")
    else:
        conversation = get_conversation(actor, conversation_id)

    route = ROUTE if is_job_match_request(prompt) else UNSUPPORTED_ROUTE
    request_message = record_message(conversation, sender_type="USER", content=prompt, intent=route)
    started = monotonic()
    result = run_job_matching_agent(actor, prompt)
    latency_ms = int((monotonic() - started) * 1000)
    success = not result.get("error_code")

    response_message = None
    if success:
        response_message = record_message(
            conversation,
            sender_type="ASSISTANT",
            content=result["reply"],
            intent=ROUTE,
        )

    execution = record_execution(
        request_message,
        route=route,
        status="SUCCEEDED" if success else "FAILED",
        agent_version=AGENT_VERSION,
        response_message=response_message,
        latency_ms=latency_ms,
        error_code=result.get("error_code", ""),
    )
    if tool_call := result.get("tool_call"):
        record_tool_call(
            execution,
            {
                "tool_name": tool_call["tool_name"],
                "input_json": tool_call["input"],
                "output_summary_json": tool_call["output"],
                "status": tool_call["status"],
                "latency_ms": tool_call["latency_ms"],
                "error_code": tool_call["error_code"],
            },
        )

    return {
        "conversation_id": str(conversation.id),
        "execution_id": str(execution.id),
        "message_id": str(response_message.id) if response_message else None,
        "reply": response_message.content if response_message else None,
        "error_code": execution.error_code or None,
    }
