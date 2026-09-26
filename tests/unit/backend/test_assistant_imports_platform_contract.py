from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from django.db.models import ForeignKey
from django.urls import resolve

from backend.apps.assistant.api.serializers import ActionReadSerializer, ToolCallReadSerializer
from backend.apps.assistant.models import AgentAction
from backend.apps.assistant.services.records import propose_action, record_execution
from backend.apps.imports.api.serializers import SourceWriteSerializer
from backend.apps.imports.models import ImportRow
from backend.apps.imports.services.records import list_sources
from backend.apps.recruitment.models import JobOffer
from backend.common.exceptions import DomainPermissionError, DomainValidationError

pytestmark = pytest.mark.unit


def _actions(path: str) -> dict[str, str]:
    return cast(Any, resolve(path).func).actions


def test_public_routes_do_not_accept_trace_or_import_writes() -> None:
    key = "00000000-0000-0000-0000-000000000001"
    assert _actions(f"/api/v1/conversations/{key}/messages/") == {"get": "list"}
    assert _actions(f"/api/v1/agent-executions/{key}/tool-calls/") == {"get": "list"}
    assert _actions(f"/api/v1/agent-executions/{key}/actions/") == {"get": "list"}
    assert _actions(f"/api/v1/import-batches/{key}/rows/") == {"get": "list"}
    assert _actions(f"/api/v1/data-sources/{key}/authorize/") == {"post": "authorize"}
    assert _actions(f"/api/v1/audit-logs/{key}/") == {"get": "retrieve"}
    assert _actions(f"/api/v1/notifications/{key}/mark-read/") == {"post": "mark_read"}


def test_trace_serializer_excludes_tool_inputs_and_action_key() -> None:
    assert "input_json" not in ToolCallReadSerializer().fields
    assert "output_summary_json" not in ToolCallReadSerializer().fields
    assert "idempotency_key" not in ActionReadSerializer().fields
    assert "is_authorized" not in SourceWriteSerializer().fields


def test_source_link_and_row_number_constraint_are_owned_by_models() -> None:
    assert isinstance(JobOffer._meta.get_field("source"), ForeignKey)
    assert JobOffer._meta.get_field("source").remote_field.model._meta.label == "imports.DataSource"
    assert any(
        constraint.name == "import_rows_batch_row_unique"
        for constraint in ImportRow._meta.constraints
    )
    assert AgentAction._meta.get_field("idempotency_key").unique


def test_execution_rejects_cross_conversation_response_before_write() -> None:
    request = SimpleNamespace(sender_type="USER", conversation_id=uuid4())
    response = SimpleNamespace(sender_type="ASSISTANT", conversation_id=uuid4())
    with pytest.raises(DomainValidationError):
        record_execution(
            cast(Any, request),
            route="chat",
            status="COMPLETED",
            agent_version="v1",
            response_message=cast(Any, response),
        )


def test_action_requires_replay_key_before_write() -> None:
    with pytest.raises(DomainValidationError):
        propose_action(
            cast(Any, SimpleNamespace()),
            action_type="APPLY",
            target_type="offer",
            target_id=None,
            idempotency_key="",
        )


def test_inactive_user_cannot_read_source_configuration() -> None:
    with pytest.raises(DomainPermissionError):
        list_sources(cast(Any, SimpleNamespace(is_active=False)))
