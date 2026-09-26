import pytest

from backend.apps.recruitment.api.job_offers_serializers import (
    JobOfferCreateSerializer,
    JobOfferReadSerializer,
    JobOfferUpdateSerializer,
)

pytestmark = pytest.mark.unit

PROTECTED = {
    "id",
    "status",
    "published_at",
    "closed_at",
    "created_by_id",
    "source_id",
    "external_id",
    "created_at",
    "updated_at",
    "deleted_at",
}


def test_create_serializer_does_not_accept_protected_fields() -> None:
    fields = set(JobOfferCreateSerializer().fields)
    assert "organization_id" in fields
    assert not fields & PROTECTED


def test_update_serializer_cannot_move_an_offer_to_another_organization() -> None:
    fields = set(JobOfferUpdateSerializer().fields)
    assert "organization_id" not in fields
    assert not fields & PROTECTED


def test_read_serializer_is_read_only_and_hides_soft_delete_marker() -> None:
    serializer = JobOfferReadSerializer()
    assert "deleted_at" not in serializer.fields
    assert all(field.read_only for field in serializer.fields.values())


def test_salary_and_external_url_validation() -> None:
    serializer = JobOfferCreateSerializer(
        data={
            "organization_id": "00000000-0000-0000-0000-000000000001",
            "title": "Engineer",
            "description": "Build things",
            "easy_apply": False,
            "min_salary": "2000.00",
            "max_salary": "3000.00",
            "offer_url": "http://example.com/apply",
        }
    )
    assert not serializer.is_valid()
    assert "offer_url" in serializer.errors
