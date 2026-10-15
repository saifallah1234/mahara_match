from typing import Any
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.recruitment.models import JobOffer

pytestmark = pytest.mark.django_db
PDF = b"%PDF-1.7\nworkspace test\n%%EOF"


def client_for(user: Any) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@patch("backend.apps.documents.services.documents.object_storage.download_object", return_value=PDF)
@patch("backend.apps.documents.services.documents.object_storage.upload_object")
def test_candidate_workspace_api_flow(
    upload_object: Any, download_object: Any, phase3: dict[str, Any]
) -> None:
    client = client_for(phase3["candidate"])
    assert (
        client.patch(reverse("user-me"), {"first_name": "Updated", "phone": "+21612345678"}).json()[
            "first_name"
        ]
        == "Updated"
    )
    assert (
        client.patch(
            reverse("candidate-profile-me"), {"headline": "Developer", "governorate": "Tunis"}
        ).json()["headline"]
        == "Developer"
    )
    experience = client.post(
        reverse("experience-list"),
        {"organization_name": "Acme", "job_title": "Developer", "start_date": "2024-01-01"},
    )
    assert experience.status_code == 201
    assert client.get(reverse("experience-list")).json()["results"][0]["job_title"] == "Developer"

    offers = [
        JobOffer.objects.create(
            organization=phase3["recruiter_org"],
            created_by=phase3["recruiter"],
            title=f"Developer {index}",
            description="Python",
            governorate="Tunis",
            contract_type="CDI",
            easy_apply=True,
            status="PUBLISHED",
            published_at=timezone.now(),
        )
        for index in range(2)
    ]
    first = client.get(
        reverse("job-offer-list"),
        {
            "status": "PUBLISHED",
            "search": "Developer",
            "governorate": "Tunis",
            "page_size": 1,
            "page": 1,
        },
    ).json()
    second = client.get(
        reverse("job-offer-list"),
        {
            "status": "PUBLISHED",
            "search": "Developer",
            "governorate": "Tunis",
            "page_size": 1,
            "page": 2,
        },
    ).json()
    assert first["count"] == 2
    assert {first["results"][0]["id"], second["results"][0]["id"]} == {
        str(offer.id) for offer in offers
    }
    assert first["results"][0]["organization_name"] == phase3["recruiter_org"].legal_name

    invalid = client.post(
        reverse("document-list"),
        {
            "file": SimpleUploadedFile("cv.pdf", b"invalid", content_type="application/pdf"),
            "type": "CV",
        },
        format="multipart",
    )
    assert invalid.status_code == 400
    uploaded = client.post(
        reverse("document-list"),
        {"file": SimpleUploadedFile("cv.pdf", PDF, content_type="application/pdf"), "type": "CV"},
        format="multipart",
    )
    assert uploaded.status_code == 201
    upload_object.assert_called_once()
    document_id = uploaded.json()["id"]
    created = client.post(
        reverse("cv-list"),
        {"document": document_id, "title": "Mon CV", "is_primary": True},
        format="json",
    )
    assert created.status_code == 201
    cv_id = created.json()["id"]
    assert client.get(reverse("cv-list")).json()["count"] == 1
    download = client.get(reverse("document-download", args=(document_id,)))
    assert download.status_code == 200
    assert b"".join(download.streaming_content) == PDF
    download_object.assert_called_once()

    application = client.post(
        reverse("application-list"), {"offer_id": str(offers[0].id), "cv_id": cv_id}, format="json"
    )
    assert application.status_code == 201
    application_id = application.json()["id"]
    assert application.json()["offer_title"] == offers[0].title
    withdrawal = client.post(
        reverse("application-transition", args=(application_id,)),
        {"status": "WITHDRAWN"},
        format="json",
    )
    assert withdrawal.status_code == 200
    assert withdrawal.json()["status"] == "WITHDRAWN"
    assert client.get(reverse("application-status-history-list")).json()["count"] == 2

    enrollment = client.post(
        reverse("training:enrollment-list"),
        {"session_id": str(phase3["session"].id)},
        format="json",
    )
    assert enrollment.status_code == 201
    enrollment_id = enrollment.json()["id"]
    assert client.get(reverse("training:enrollment-list")).json()["count"] == 1
    assert (
        client.delete(reverse("training:enrollment-detail", args=(enrollment_id,))).status_code
        == 204
    )
    assert (
        client.get(reverse("training:enrollment-detail", args=(enrollment_id,))).json()["status"]
        == "DROPPED"
    )
