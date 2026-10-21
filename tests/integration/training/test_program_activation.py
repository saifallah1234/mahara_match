# Placement: tests/integration/training/test_program_activation.py
from typing import Any

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from backend.apps.taxonomy.models import Skill
from backend.apps.training.models import TrainingProgram, TrainingSkill

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _client(phase3: dict[str, Any]) -> APIClient:
    client = APIClient()
    client.force_authenticate(phase3["provider"])
    return client


def _draft(phase3: dict[str, Any]) -> TrainingProgram:
    return TrainingProgram.objects.create(
        organization=phase3["provider_org"],
        title="Draft programme",
        status="DRAFT",
        delivery_mode="ONLINE",
    )


def test_program_cannot_be_created_active_without_skill(phase3: dict[str, Any]) -> None:
    response = _client(phase3).post(
        reverse("training:program-list"),
        {
            "organization_id": str(phase3["provider_org"].id),
            "title": "New programme",
            "status": "ACTIVE",
        },
        format="json",
    )

    assert response.status_code == 400
    assert not TrainingProgram.objects.filter(title="New programme").exists()


def test_program_cannot_be_activated_without_skill(phase3: dict[str, Any]) -> None:
    program = _draft(phase3)

    response = _client(phase3).patch(
        reverse("training:program-detail", args=[program.id]), {"status": "ACTIVE"}, format="json"
    )

    assert response.status_code == 400
    program.refresh_from_db()
    assert program.status == "DRAFT"


def test_program_activates_once_it_has_a_skill(phase3: dict[str, Any]) -> None:
    program = _draft(phase3)
    TrainingSkill.objects.create(
        program=program,
        skill=Skill.objects.create(canonical_name="Excel"),
        target_level="INTERMEDIATE",
    )

    response = _client(phase3).patch(
        reverse("training:program-detail", args=[program.id]), {"status": "ACTIVE"}, format="json"
    )

    assert response.status_code == 200
    program.refresh_from_db()
    assert program.status == "ACTIVE"
