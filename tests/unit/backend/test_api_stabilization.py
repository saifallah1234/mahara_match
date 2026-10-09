from typing import Any, cast
from uuid import uuid4

import pytest
from django.urls import Resolver404, resolve
from drf_spectacular.generators import SchemaGenerator
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from backend.apps.assistant.api.agent_run_views import AgentRunView
from backend.apps.identity.api.organization_members_views import OrganizationMemberViewSet
from backend.apps.identity.models import User, UserStatus
from backend.apps.identity.services import organizations as organization_services
from backend.apps.training.services import programs as program_services
from backend.common.api.query_params import uuid_query_param
from backend.common.exceptions import DomainValidationError

pytestmark = pytest.mark.unit


def active_user() -> User:
    return User(
        id=uuid4(),
        email="active@example.test",
        first_name="Active",
        last_name="User",
        status=UserStatus.ACTIVE,
    )


def test_import_rows_only_expose_nested_list_and_standalone_detail() -> None:
    with pytest.raises(Resolver404):
        resolve("/api/v1/import-rows/")

    detail = cast(Any, resolve(f"/api/v1/import-rows/{uuid4()}/").func)
    nested = cast(Any, resolve(f"/api/v1/import-batches/{uuid4()}/rows/").func)
    assert detail.actions == {"get": "retrieve"}
    assert {method: action for method, action in nested.actions.items() if method != "head"} == {
        "get": "list"
    }


def test_organization_members_list_uses_standard_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.apps.identity.api.organization_members_views.member_services.list_members",
        lambda actor, organization_id: [],
    )
    request = APIRequestFactory().get("/api/v1/organizations/members/")
    force_authenticate(request, active_user())

    response = OrganizationMemberViewSet.as_view({"get": "list"})(request, organization_id=uuid4())

    assert response.status_code == 200
    assert response.data == {"count": 0, "next": None, "previous": None, "results": []}


def test_agent_failure_uses_the_shared_error_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    result = {
        "conversation_id": str(uuid4()),
        "execution_id": str(uuid4()),
        "message_id": None,
        "reply": None,
        "error_code": "llm_unavailable",
    }
    monkeypatch.setattr(
        "backend.apps.assistant.api.agent_run_views.own_profile", lambda actor: object()
    )
    monkeypatch.setattr(
        "backend.apps.assistant.api.agent_run_views.start_agent_run",
        lambda actor, message, conversation_id: result,
    )
    request = APIRequestFactory().post(
        "/api/v1/agent-runs/", {"message": "Find matching jobs."}, format="json"
    )
    force_authenticate(request, active_user())

    response = AgentRunView.as_view()(request)

    assert response.status_code == 503
    assert response.data["error"] == {
        "code": "llm_unavailable",
        "message": "The agent run could not be completed.",
        "details": result,
    }


def test_uuid_query_parameters_are_validated_before_service_calls() -> None:
    request = Request(APIRequestFactory().get("/endpoint/?organization_id=not-a-uuid"))
    with pytest.raises(DomainValidationError) as error:
        uuid_query_param(request, "organization_id")
    assert error.value.details == {"organization_id": ["Enter a valid UUID."]}


def test_normal_catalog_queries_exclude_deleted_organizations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(organization_services, "require_permission", lambda *args: None)
    monkeypatch.setattr(program_services, "require_permission", lambda *args, **kwargs: None)

    organization_sql = str(organization_services.list_organizations(active_user()).query)
    program_sql = str(program_services.list_programs(active_user()).query)

    assert '"organizations"."deleted_at" IS NULL' in organization_sql
    assert '"organizations"."deleted_at" IS NULL' in program_sql
    assert '"organizations"."verification_status" = VERIFIED' in program_sql


def test_openapi_uses_write_contracts_and_has_no_broken_import_collection() -> None:
    schema = SchemaGenerator().get_schema(public=True)
    paths = cast(dict[str, Any], schema["paths"])

    assert "/api/v1/import-rows/" not in paths
    assert (
        paths["/api/v1/data-sources/"]["post"]["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        == "#/components/schemas/SourceWrite"
    )
    assert (
        paths["/api/v1/training/enrollments/"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/TrainingEnrollmentCreate"
    )
    assert paths["/api/v1/agent-runs/"]["post"]["responses"]["503"]["content"]

    token = paths["/api/v1/auth/token/"]["post"]
    assert token["requestBody"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/EmailTokenObtainPair"
    )
    assert token["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/AccessToken"
    )
    assert {parameter["name"] for parameter in token["parameters"]} == {
        "X-CSRFToken",
        "csrftoken",
    }

    refresh = paths["/api/v1/auth/token/refresh/"]["post"]
    assert "requestBody" not in refresh
    assert {parameter["name"] for parameter in refresh["parameters"]} == {
        "X-CSRFToken",
        "csrftoken",
        "mahara_refresh",
    }
    assert paths["/api/v1/auth/csrf/"]["get"]["responses"] == {
        "204": {"description": "No response body"}
    }
    assert (
        paths["/api/v1/users/{id}/status/"]["post"]["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        == "#/components/schemas/UserStatusUpdate"
    )
