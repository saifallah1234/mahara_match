# Placement: tests/integration/training/test_catalogue_sessions.py
from datetime import timedelta
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.training.models import TrainingProgram, TrainingSession

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _session(program: TrainingProgram) -> TrainingSession:
    now = timezone.now()
    return TrainingSession.objects.create(
        program=program,
        start_date=now + timedelta(days=5),
        end_date=now + timedelta(days=6),
        registration_deadline=now + timedelta(days=4),
        capacity=10,
        location_or_url="Sfax classroom",
    )


def test_candidate_lists_visible_sessions_of_every_program_in_one_call(
    phase3: dict[str, Any],
) -> None:
    draft = TrainingProgram.objects.create(
        organization=phase3["provider_org"],
        title="Not yet published",
        status="DRAFT",
        delivery_mode="ONLINE",
    )
    _session(draft)
    client = APIClient()
    client.force_authenticate(phase3["candidate"])

    response = client.get(reverse("training:session-list"))

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [str(phase3["session"].id)]


def test_catalogue_listing_still_filters_by_program_when_asked(phase3: dict[str, Any]) -> None:
    other = TrainingProgram.objects.create(
        organization=phase3["provider_org"],
        title="Second programme",
        status="ACTIVE",
        delivery_mode="ONLINE",
    )
    _session(other)
    client = APIClient()
    client.force_authenticate(phase3["candidate"])

    response = client.get(
        reverse("training:session-list"), {"program_id": str(phase3["program"].id)}
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [str(phase3["session"].id)]
