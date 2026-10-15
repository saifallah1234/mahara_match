from typing import Any, cast

import pytest
from django.urls import resolve

pytestmark = pytest.mark.unit

UUID_PATH = "00000000-0000-0000-0000-000000000001"


def _actions(path: str) -> dict[str, str]:
    return {
        method: action
        for method, action in cast(Any, resolve(path).func).actions.items()
        if method != "head"
    }


# Route tests pass once P1 includes the recruitment urls under /api/v1/.
def test_offer_skill_detail_allows_read_patch_and_remove_only() -> None:
    assert _actions(f"/api/v1/offer-skills/{UUID_PATH}/") == {
        "get": "retrieve",
        "patch": "partial_update",
        "delete": "destroy",
    }


def test_offer_skill_collection_allows_list_and_create() -> None:
    assert _actions("/api/v1/offer-skills/") == {"get": "list", "post": "create"}


@pytest.mark.parametrize(
    "resource",
    ["application-status-history"],
)
def test_read_only_resources_expose_only_get(resource: str) -> None:
    assert _actions(f"/api/v1/{resource}/") == {"get": "list"}
    assert _actions(f"/api/v1/{resource}/{UUID_PATH}/") == {"get": "retrieve"}


@pytest.mark.parametrize("resource", ["applications", "interviews"])
def test_lifecycle_resources_expose_controlled_actions(resource: str) -> None:
    assert _actions(f"/api/v1/{resource}/") == {"get": "list", "post": "create"}
    assert _actions(f"/api/v1/{resource}/{UUID_PATH}/") == {"get": "retrieve"}
    assert _actions(f"/api/v1/{resource}/{UUID_PATH}/transition/") == {"post": "transition"}


def test_application_exposes_submitted_cv_download() -> None:
    assert _actions(f"/api/v1/applications/{UUID_PATH}/cv/") == {"get": "cv"}
