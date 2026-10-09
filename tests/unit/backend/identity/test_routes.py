from typing import Any, cast

import pytest
from django.urls import resolve

pytestmark = pytest.mark.unit


def _actions(path: str) -> dict[str, str]:
    actions = cast(Any, resolve(path).func).actions
    return {method: action for method, action in actions.items() if method != "head"}


def test_role_detail_exposes_patch_but_not_put_or_delete() -> None:
    assert _actions("/api/v1/roles/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve",
        "patch": "partial_update",
    }


def test_user_detail_has_no_delete_operation() -> None:
    assert _actions("/api/v1/users/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
    }


def test_user_status_is_a_separate_action() -> None:
    assert _actions("/api/v1/users/00000000-0000-0000-0000-000000000001/status/") == {
        "post": "status"
    }


def test_relationship_detail_only_allows_read_and_remove() -> None:
    assert _actions("/api/v1/user-roles/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve",
        "delete": "destroy",
    }
