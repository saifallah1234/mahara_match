from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from backend.apps.assistant.models import (
    AgentAction,
    AgentExecution,
    AgentToolCall,
    Conversation,
    ConversationMessage,
)
from backend.apps.identity.models import User
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_conversations(actor: User) -> QuerySet[Conversation]:
    return Conversation.objects.filter(user=actor, deleted_at__isnull=True)


def get_conversation(actor: User, conversation_id: UUID | str) -> Conversation:
    try:
        return list_conversations(actor).get(pk=conversation_id)
    except Conversation.DoesNotExist as exc:
        raise DomainNotFoundError("Conversation not found.") from exc


def create_conversation(actor: User, title: str = "") -> Conversation:
    return Conversation.objects.create(user=actor, title=title)


def rename_conversation(actor: User, conversation_id: UUID | str, title: str) -> Conversation:
    conversation = get_conversation(actor, conversation_id)
    conversation.title = title
    conversation.save(update_fields=["title", "updated_at"])
    return conversation


def delete_conversation(actor: User, conversation_id: UUID | str) -> None:
    conversation = get_conversation(actor, conversation_id)
    conversation.deleted_at = timezone.now()
    conversation.status = "DELETED"
    conversation.save(update_fields=["deleted_at", "status", "updated_at"])


def list_messages(actor: User, conversation_id: UUID | str) -> QuerySet[ConversationMessage]:
    conversation = get_conversation(actor, conversation_id)
    return conversation.messages.all()


@transaction.atomic
def record_message(
    conversation: Conversation,
    *,
    sender_type: str,
    content: str,
    intent: str = "",
    citations: list[dict[str, Any]] | None = None,
) -> ConversationMessage:
    """Trusted assistant runtime entrypoint; no public message creation route."""
    if conversation.deleted_at is not None or sender_type not in {"USER", "ASSISTANT", "SYSTEM"}:
        raise DomainValidationError(details={"message": ["Invalid conversation or sender."]})
    message = ConversationMessage.objects.create(
        conversation=conversation,
        sender_type=sender_type,
        content=content,
        intent=intent,
        citations_json=citations or [],
    )
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message_at", "updated_at"])
    return message


def record_execution(
    request_message: ConversationMessage,
    *,
    route: str,
    status: str,
    agent_version: str,
    response_message: ConversationMessage | None = None,
    latency_ms: int | None = None,
    error_code: str = "",
) -> AgentExecution:
    if request_message.sender_type != "USER" or (
        response_message is not None
        and (
            response_message.sender_type != "ASSISTANT"
            or response_message.conversation_id != request_message.conversation_id
        )
    ):
        raise DomainValidationError(details={"messages": ["Invalid execution message links."]})
    return AgentExecution.objects.create(
        request_message=request_message,
        response_message=response_message,
        route=route,
        status=status,
        agent_version=agent_version,
        latency_ms=latency_ms,
        error_code=error_code,
    )


def record_tool_call(execution: AgentExecution, data: Mapping[str, Any]) -> AgentToolCall:
    return AgentToolCall.objects.create(execution=execution, **data)


def propose_action(
    execution: AgentExecution,
    *,
    action_type: str,
    target_type: str,
    target_id: UUID | None,
    idempotency_key: str,
) -> AgentAction:
    if not idempotency_key:
        raise DomainValidationError(details={"idempotency_key": ["Required."]})
    action, created = AgentAction.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "execution": execution,
            "action_type": action_type,
            "target_type": target_type,
            "target_id": target_id,
        },
    )
    if not created and (
        action.execution_id != execution.id
        or action.action_type != action_type
        or action.target_type != target_type
        or action.target_id != target_id
    ):
        raise DomainValidationError(details={"idempotency_key": ["Key reused for another action."]})
    return action


def list_executions(actor: User) -> QuerySet[AgentExecution]:
    return AgentExecution.objects.filter(
        request_message__conversation__user=actor,
        request_message__conversation__deleted_at__isnull=True,
    )


def get_execution(actor: User, execution_id: UUID | str) -> AgentExecution:
    try:
        return list_executions(actor).get(pk=execution_id)
    except AgentExecution.DoesNotExist as exc:
        raise DomainNotFoundError("Execution not found.") from exc


def list_tool_calls(actor: User, execution_id: UUID | str) -> QuerySet[AgentToolCall]:
    execution = get_execution(actor, execution_id)
    return execution.tool_calls.all()


def list_actions(actor: User, execution_id: UUID | str) -> QuerySet[AgentAction]:
    execution = get_execution(actor, execution_id)
    return execution.actions.all()
