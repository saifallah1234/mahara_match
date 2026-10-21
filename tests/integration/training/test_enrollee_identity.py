# Placement: tests/integration/training/test_enrollee_identity.py
from typing import Any

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from backend.apps.training.models import TrainingEnrollment

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _client(user: Any) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_provider_sees_applicant_identity_of_enrollee(phase3: dict[str, Any]) -> None:
    enrollment = TrainingEnrollment.objects.create(
        session=phase3["session"], candidate=phase3["candidate_profile"], status="REGISTERED"
    )

    response = _client(phase3["provider"]).get(
        reverse("training:enrollment-detail", args=[enrollment.id])
    )

    assert response.status_code == 200
    assert response.json()["applicant"] == {
        "first_name": "Private",
        "last_name": "Identity",
        "email": "candidate@example.test",
    }


def test_candidate_own_enrollment_has_no_applicant_object(phase3: dict[str, Any]) -> None:
    enrollment = TrainingEnrollment.objects.create(
        session=phase3["session"], candidate=phase3["candidate_profile"], status="REGISTERED"
    )

    response = _client(phase3["candidate"]).get(
        reverse("training:enrollment-detail", args=[enrollment.id])
    )

    assert response.status_code == 200
    assert "applicant" not in response.json()


def test_other_provider_cannot_read_enrollee_identity(phase3: dict[str, Any]) -> None:
    enrollment = TrainingEnrollment.objects.create(
        session=phase3["session"], candidate=phase3["candidate_profile"], status="REGISTERED"
    )

    response = _client(phase3["other_provider"]).get(
        reverse("training:enrollment-detail", args=[enrollment.id])
    )

    assert response.status_code in {403, 404}
    assert "candidate@example.test" not in response.content.decode()
