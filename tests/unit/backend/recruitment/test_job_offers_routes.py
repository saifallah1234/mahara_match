from typing import Any, cast

import pytest
from django.urls import resolve

pytestmark = pytest.mark.unit


def _actions(path: str) -> dict[str, str]:
    return cast(Any, resolve(path).func).actions


# These tests pass once P1 includes backend.apps.recruitment.api.urls under /api/v1/.
def test_job_offer_detail_has_no_delete_operation() -> None:
    assert _actions("/api/v1/job-offers/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
    }


def test_job_offer_collection_allows_list_and_create_only() -> None:
    assert _actions("/api/v1/job-offers/") == {"get": "list", "post": "create"}
