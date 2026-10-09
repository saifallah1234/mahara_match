from typing import Any

import pytest

from backend.apps.matching.api.offer_matches_serializers import OfferMatchReadSerializer
from backend.apps.matching.models import OfferMatch

pytestmark = pytest.mark.unit


def test_read_serializer_is_read_only() -> None:
    assert all(field.read_only for field in OfferMatchReadSerializer().fields.values())


def test_match_constraints_are_declared() -> None:
    names = {constraint.name for constraint in OfferMatch._meta.constraints}
    assert "offer_matches_candidate_offer_version_unique" in names
    assert {
        "offer_matches_overall_score_0_100",
        "offer_matches_skill_score_0_100",
        "offer_matches_experience_score_0_100",
        "offer_matches_location_score_0_100",
    } <= names


def test_offer_matches_route_is_read_only() -> None:
    from django.urls import resolve

    func: Any = resolve("/api/v1/offer-matches/").func
    assert {method: action for method, action in func.actions.items() if method != "head"} == {
        "get": "list"
    }
