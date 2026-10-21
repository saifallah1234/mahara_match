# Placement: tests/integration/recruitment/test_applicant_identity.py
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.candidates.models import CV
from backend.apps.documents.models import Document
from backend.apps.recruitment.models import Application, JobOffer

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _client(user: Any) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def private_application(phase3: dict[str, Any]) -> Application:
    phase3["candidate"].phone = "+21620123456"
    phase3["candidate"].save(update_fields=["phone"])
    phase3["candidate_profile"].profile_visibility = "PRIVATE"
    phase3["candidate_profile"].save(update_fields=["profile_visibility"])
    offer = JobOffer.objects.create(
        organization=phase3["recruiter_org"],
        created_by=phase3["recruiter"],
        title="Python developer",
        description="Build tested services",
        easy_apply=True,
        status="PUBLISHED",
    )
    document = Document.objects.create(
        owner_user=phase3["candidate"],
        type="CV",
        storage_uri="private/cv",
        file_name="cv.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        uploaded_at=timezone.now(),
    )
    cv = CV.objects.create(
        candidate=phase3["candidate_profile"], document=document, title="CV", version_number=1
    )
    return Application.objects.create(
        candidate=phase3["candidate_profile"], offer=offer, cv=cv, status="SUBMITTED"
    )


def test_receiving_recruiter_sees_applicant_identity_of_private_candidate(
    phase3: dict[str, Any], private_application: Application
) -> None:
    client = _client(phase3["recruiter"])

    response = client.get(reverse("application-detail", args=[private_application.id]))

    assert response.status_code == 200
    body = response.json()
    assert body["applicant"] == {
        "first_name": "Private",
        "last_name": "Identity",
        "email": "candidate@example.test",
    }
    assert body["candidate_profile"]["id"] == str(phase3["candidate_profile"].id)
    assert "birth_date" not in body["candidate_profile"]
    assert "+21620123456" not in response.content.decode()


def test_identity_stays_visible_on_terminal_applications(
    phase3: dict[str, Any], private_application: Application
) -> None:
    private_application.status = "REJECTED"
    private_application.save(update_fields=["status"])

    response = _client(phase3["recruiter"]).get(reverse("application-list"))

    assert response.json()["results"][0]["applicant"]["email"] == "candidate@example.test"


def test_other_organization_recruiter_still_gets_not_found(
    phase3: dict[str, Any], private_application: Application
) -> None:
    response = _client(phase3["other_recruiter"]).get(
        reverse("application-detail", args=[private_application.id])
    )

    assert response.status_code == 404


def test_candidate_own_reads_have_no_applicant_object(
    phase3: dict[str, Any], private_application: Application
) -> None:
    response = _client(phase3["candidate"]).get(
        reverse("application-detail", args=[private_application.id])
    )

    assert response.status_code == 200
    assert "applicant" not in response.json()
    assert "candidate_profile" not in response.json()
