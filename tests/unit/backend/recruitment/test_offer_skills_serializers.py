import pytest

from backend.apps.recruitment.api.offer_skills_serializers import (
    OfferSkillCreateSerializer,
    OfferSkillReadSerializer,
    OfferSkillUpdateSerializer,
)

pytestmark = pytest.mark.unit


def test_create_serializer_fields() -> None:
    assert set(OfferSkillCreateSerializer().fields) == {
        "offer_id",
        "skill_id",
        "importance",
        "required_level",
        "is_mandatory",
    }


def test_update_serializer_cannot_change_offer_or_skill() -> None:
    assert set(OfferSkillUpdateSerializer().fields) == {
        "importance",
        "required_level",
        "is_mandatory",
    }


def test_read_serializer_is_read_only() -> None:
    assert all(field.read_only for field in OfferSkillReadSerializer().fields.values())
