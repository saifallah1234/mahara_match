from __future__ import annotations

from time import monotonic
from typing import TYPE_CHECKING, Any
from uuid import UUID

from ai.agents.anetai import AGENT_VERSION, resolve_route, run_agent
from ai.agents.intents import Role
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


def citations_for(evidence: dict[str, Any]) -> list[dict[str, str]]:
    """One source per returned offer, profile or training program: IDs and labels only."""
    found: dict[str, dict[str, str]] = {}

    def cite(reference: str, label: str) -> None:
        found.setdefault(reference, {"label": label, "reference": reference})

    if "analysis_id" in evidence:
        label = f"Analyse ATS : {evidence['cv_title']} v{evidence['cv_version']}"
        cite(f"cv_analysis:{evidence['analysis_id']}", label)
    for match in evidence.get("matches", []):
        if "profile_id" in match:
            cite(f"candidate_profile:{match['profile_id']}", f"Profil n°{match['rank']}")
        if "offer_id" in match:
            cite(f"offer:{match['offer_id']}", match["title"])
            for program in match.get("training", []):
                cite(f"program:{program['program_id']}", program["title"])
    return list(found.values())


def start_agent_run(
    actor: User,
    prompt: str,
    conversation_id: UUID | str | None = None,
    role: Role = "candidate",
) -> dict[str, Any]:
    conversation: Conversation
    if conversation_id is None:
        # The first question names the conversation in the user's own language.
        title = " ".join(prompt.split())
        conversation = create_conversation(actor, title[:77] + "…" if len(title) > 80 else title)
    else:
        conversation = get_conversation(actor, conversation_id)

    route = resolve_route(role, prompt)
    request_message = record_message(conversation, sender_type="USER", content=prompt, intent=route)
    started = monotonic()
    result = run_agent(actor, prompt, role)
    latency_ms = int((monotonic() - started) * 1000)
    success = not result.get("error_code")

    response_message = None
    if success:
        response_message = record_message(
            conversation,
            sender_type="ASSISTANT",
            content=result["reply"],
            intent=route,
            citations=citations_for(result.get("evidence", {})),
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
