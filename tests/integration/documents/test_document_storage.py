from collections.abc import Iterator
from hashlib import sha256
from typing import cast
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import StreamingHttpResponse
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.documents.models import Document
from backend.apps.identity.models import User, UserStatus

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.7\nsynthetic document\n%%EOF"


def streamed(response: object) -> bytes:
    content = cast(StreamingHttpResponse, response).streaming_content
    return b"".join(cast(Iterator[bytes], content))


def user(email: str) -> User:
    return User.objects.create_user(
        email,
        "test-password",
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE,
    )


def client_for(account: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(account)
    return client


def document_for(owner: User, storage_uri: str = "documents/private/object-key") -> Document:
    return Document.objects.create(
        owner_user=owner,
        type="CV",
        storage_uri=storage_uri,
        file_name="resume.pdf",
        mime_type="application/pdf",
        size_bytes=len(PDF),
        checksum=sha256(PDF).hexdigest(),
        scan_status="PENDING",
        uploaded_at=timezone.now(),
    )


@patch("backend.apps.documents.services.documents.object_storage.upload_object")
def test_successful_upload_persists_derived_metadata(upload_object) -> None:
    owner = user("owner@example.test")
    response = client_for(owner).post(
        reverse("document-list"),
        {
            "type": "CV",
            "file": SimpleUploadedFile("resume.pdf", PDF, content_type="application/pdf"),
        },
        format="multipart",
    )

    assert response.status_code == 201
    document = Document.objects.get(id=response.json()["id"])
    assert document.owner_user == owner
    assert document.type == "CV"
    assert document.file_name == "resume.pdf"
    assert document.mime_type == "application/pdf"
    assert document.size_bytes == len(PDF)
    assert document.checksum == sha256(PDF).hexdigest()
    assert document.scan_status == "PENDING"
    assert "storage_uri" not in response.json()
    assert document.storage_uri not in response.content.decode()
    upload_object.assert_called_once_with(document.storage_uri, PDF, "application/pdf")


@patch("backend.apps.documents.services.documents.object_storage.upload_object")
def test_invalid_files_and_required_metadata_are_rejected(upload_object) -> None:
    client = client_for(user("invalid@example.test"))
    cases = (
        ({"file": SimpleUploadedFile("resume.pdf", PDF, content_type="application/pdf")},),
        (
            {
                "type": "CV",
                "file": SimpleUploadedFile("resume.txt", b"text", content_type="text/plain"),
            },
        ),
        (
            {
                "type": "cv",
                "file": SimpleUploadedFile("resume.pdf", PDF, content_type="application/pdf"),
            },
        ),
        (
            {
                "type": "CV",
                "file": SimpleUploadedFile(
                    "resume.pdf", b"not a pdf", content_type="application/pdf"
                ),
            },
        ),
        (
            {
                "type": "CV",
                "file": SimpleUploadedFile("resume", PDF, content_type="application/pdf"),
            },
        ),
    )

    for (payload,) in cases:
        response = client.post(reverse("document-list"), payload, format="multipart")
        assert response.status_code == 400
        assert set(response.json()) == {"error"}

    with override_settings(DOCUMENT_MAX_UPLOAD_BYTES=len(PDF) - 1):
        too_large = client.post(
            reverse("document-list"),
            {
                "type": "CV",
                "file": SimpleUploadedFile("resume.pdf", PDF, content_type="application/pdf"),
            },
            format="multipart",
        )
    assert too_large.status_code == 400
    upload_object.assert_not_called()
    assert Document.objects.count() == 0


@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_unauthorized_and_cross_user_downloads_do_not_reach_storage(download_object) -> None:
    owner = user("private-owner@example.test")
    document = document_for(owner)

    anonymous = APIClient().get(reverse("document-download", args=(document.id,)))
    other = client_for(user("other@example.test")).get(
        reverse("document-download", args=(document.id,))
    )

    assert anonymous.status_code == 401
    assert other.status_code == 404
    download_object.assert_not_called()


@patch(
    "backend.apps.documents.services.documents.object_storage.download_object",
    return_value=PDF,
)
def test_owner_can_download_through_backend(download_object) -> None:
    owner = user("download@example.test")
    document = document_for(owner)

    response = client_for(owner).get(reverse("document-download", args=(document.id,)))

    assert response.status_code == 200
    assert streamed(response) == PDF
    assert response["Content-Type"] == "application/pdf"
    assert "attachment" in response["Content-Disposition"]
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Content-Type-Options"] == "nosniff"
    download_object.assert_called_once_with(document.storage_uri)


@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_nonexistent_document_returns_shared_not_found_error(download_object) -> None:
    response = client_for(user("missing@example.test")).get(
        reverse("document-download", args=("00000000-0000-0000-0000-000000000001",))
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    download_object.assert_not_called()


def test_storage_information_is_not_exposed() -> None:
    owner = user("metadata@example.test")
    secret = "documents/private/never-expose-this-key"
    document = document_for(owner, secret)
    client = client_for(owner)

    detail = client.get(reverse("document-detail", args=(document.id,)))
    listing = client.get(reverse("document-list"))

    assert detail.status_code == 200
    assert "storage_uri" not in detail.json()
    assert secret not in detail.content.decode()
    assert secret not in listing.content.decode()
