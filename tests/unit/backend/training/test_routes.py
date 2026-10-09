from typing import Any, cast

import pytest
from django.urls import resolve

pytestmark = pytest.mark.unit


def _actions(path: str) -> dict[str, str]:
    return {
        method: action
        for method, action in cast(Any, resolve(path).func).actions.items()
        if method != "head"
    }


def test_program_detail_allows_full_crud() -> None:
    assert _actions("/api/v1/training/programs/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }


def test_session_detail_allows_full_crud() -> None:
    assert _actions("/api/v1/training/sessions/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }


def test_skill_detail_only_allows_read_and_remove() -> None:
    assert _actions("/api/v1/training/skills/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve",
        "delete": "destroy",
    }


def test_enrollment_detail_disallows_direct_edits() -> None:
    assert _actions("/api/v1/training/enrollments/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve",
        "delete": "destroy",
    }


def test_enrollment_progress_is_a_dedicated_patch_only_action() -> None:
    assert _actions(
        "/api/v1/training/enrollments/00000000-0000-0000-0000-000000000001/progress/"
    ) == {"patch": "progress"}


def test_recommendation_detail_is_read_only() -> None:
    assert _actions("/api/v1/training/recommendations/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve",
    }
