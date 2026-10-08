from collections.abc import Iterator
from hashlib import sha256
from typing import cast
from unittest.mock import patch

import pytest
from django.http import StreamingHttpResponse
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from backend.apps.candidates.models import CV, CandidateProfile
from backend.apps.documents.models import Document
from backend.apps.identity.models import (
    Organization,
    OrganizationMember,
    OrganizationType,
    Role,
    RoleCode,
    User,
    UserRole,
    UserStatus,
)
from backend.apps.identity.models.organizations import VerificationStatus
from backend.apps.identity.services.bootstrap import seed_identity_rbac
from backend.apps.recruitment.models import (
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
    JobOffer,
    JobOfferStatus,
)
from backend.apps.recruitment.services.bootstrap import seed_recruitment_rbac

pytestmark = pytest.mark.django_db

PDF_V1 = b"%PDF-1.7\nversion one\n%%EOF"
PDF_V2 = b"%PDF-1.7\nversion two\n%%EOF"


def streamed(response: object) -> bytes:
    content = cast(StreamingHttpResponse, response).streaming_content
    return b"".join(cast(Iterator[bytes], content))


def account(email: str) -> User:
    return User.objects.create_user(
        email,
        "test-password",
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE,
    )


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def candidate(email: str = "candidate@example.test") -> tuple[User, CandidateProfile]:
    seed_identity_rbac()
    user = account(email)
    UserRole.objects.create(user=user, role=Role.objects.get(code=RoleCode.CANDIDATE))
    return user, CandidateProfile.objects.create(user=user)


def organization(number: str) -> Organization:
    return Organization.objects.create(
        type=OrganizationType.COMPANY,
        legal_name=f"Company {number}",
        registration_number=number,
        matricule_fiscal=f"{int(number):07d}A00000",
        verification_status=VerificationStatus.VERIFIED,
    )


def recruiter(user: User, org: Organization, *, with_role: bool = True) -> None:
    seed_identity_rbac()
    seed_recruitment_rbac()
    OrganizationMember.objects.create(organization=org, user=user)
    if with_role:
        UserRole.objects.create(
            user=user,
            role=Role.objects.get(code=RoleCode.RECRUITER),
            organization=org,
        )


def cv_for(
    user: User,
    profile: CandidateProfile,
    version: int,
    content: bytes,
) -> CV:
    document = Document.objects.create(
        owner_user=user,
        type="CV",
        storage_uri=f"documents/{user.id}/cv-{version}",
        file_name=f"resume-v{version}.pdf",
        mime_type="application/pdf",
        size_bytes=len(content),
        checksum=sha256(content).hexdigest(),
        scan_status="PENDING",
        uploaded_at=timezone.now(),
    )
    return CV.objects.create(
        candidate=profile,
        document=document,
        title=f"Resume v{version}",
        version_number=version,
    )


def offer_for(org: Organization) -> JobOffer:
    return JobOffer.objects.create(
        organization=org,
        created_by=account(f"owner-{org.registration_number}@example.test"),
        title="Developer",
        description="Build things",
        easy_apply=True,
        status=JobOfferStatus.PUBLISHED,
    )


def application_for(profile: CandidateProfile, cv: CV, org: Organization) -> Application:
    offer = offer_for(org)
    application = Application.objects.create(
        candidate=profile,
        offer=offer,
        cv=cv,
        status=ApplicationStatus.SUBMITTED,
        applied_at=timezone.now(),
    )
    ApplicationStatusHistory.objects.create(application=application, status=application.status)
    return application


@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_candidate_accesses_own_submitted_cv(download_object) -> None:
    user, profile = candidate()
    org = organization("1")
    cv = cv_for(user, profile, 1, PDF_V1)
    application = application_for(profile, cv, org)
    download_object.return_value = PDF_V1

    response = client_for(user).get(reverse("application-cv", args=(application.id,)))

    assert response.status_code == 200
    assert streamed(response) == PDF_V1


@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_authorized_recruiter_accesses_submitted_cv(download_object) -> None:
    user, profile = candidate()
    org = organization("2")
    cv = cv_for(user, profile, 1, PDF_V1)
    application = application_for(profile, cv, org)
    reviewer = account("reviewer@example.test")
    recruiter(reviewer, org)
    download_object.return_value = PDF_V1

    response = client_for(reviewer).get(reverse("application-cv", args=(application.id,)))

    assert response.status_code == 200
    assert streamed(response) == PDF_V1


@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_unrelated_recruiter_is_denied(download_object) -> None:
    user, profile = candidate()
    org = organization("3")
    application = application_for(profile, cv_for(user, profile, 1, PDF_V1), org)
    unrelated = account("unrelated@example.test")
    recruiter(unrelated, org, with_role=False)

    response = client_for(unrelated).get(reverse("application-cv", args=(application.id,)))

    assert response.status_code == 403
    download_object.assert_not_called()


@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_recruiter_from_another_organization_is_denied(download_object) -> None:
    user, profile = candidate()
    receiving_org = organization("4")
    application = application_for(profile, cv_for(user, profile, 1, PDF_V1), receiving_org)
    other_org = organization("5")
    outsider = account("other-org@example.test")
    recruiter(outsider, other_org)

    response = client_for(outsider).get(reverse("application-cv", args=(application.id,)))

    assert response.status_code == 404
    download_object.assert_not_called()


def test_recruiter_cannot_browse_unrelated_cvs_or_documents() -> None:
    user, profile = candidate()
    org = organization("6")
    cv = cv_for(user, profile, 1, PDF_V1)
    reviewer = account("no-browse@example.test")
    recruiter(reviewer, org)
    client = client_for(reviewer)

    assert client.get(reverse("cv-list")).status_code == 403
    assert client.get(reverse("cv-detail", args=(cv.id,))).status_code == 403
    assert client.get(reverse("document-detail", args=(cv.document_id,))).status_code == 404


@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_candidate_cannot_access_another_candidates_submitted_cv(download_object) -> None:
    owner, profile = candidate()
    application = application_for(profile, cv_for(owner, profile, 1, PDF_V1), organization("12"))
    outsider, _ = candidate("other-candidate@example.test")

    response = client_for(outsider).get(reverse("application-cv", args=(application.id,)))

    assert response.status_code == 404
    download_object.assert_not_called()


@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_application_returns_the_exact_submitted_cv_version(download_object) -> None:
    user, profile = candidate()
    org = organization("7")
    submitted = cv_for(user, profile, 1, PDF_V1)
    cv_for(user, profile, 2, PDF_V2)
    application = application_for(profile, submitted, org)
    download_object.return_value = PDF_V1

    response = client_for(user).get(reverse("application-cv", args=(application.id,)))

    assert response.status_code == 200
    assert streamed(response) == PDF_V1
    assert "resume-v1.pdf" in response["Content-Disposition"]
    download_object.assert_called_once_with(submitted.document.storage_uri)


def test_deleted_cv_disappears_from_normal_queries() -> None:
    user, profile = candidate()
    cv = cv_for(user, profile, 1, PDF_V1)
    client = client_for(user)

    assert client.delete(reverse("cv-detail", args=(cv.id,))).status_code == 204

    assert client.get(reverse("cv-detail", args=(cv.id,))).status_code == 404
    assert client.get(reverse("cv-list")).json()["count"] == 0


def test_deleted_cv_cannot_be_used_for_new_applications() -> None:
    user, profile = candidate()
    org = organization("8")
    cv = cv_for(user, profile, 1, PDF_V1)
    offer = offer_for(org)
    client = client_for(user)
    client.delete(reverse("cv-detail", args=(cv.id,)))

    response = client.post(
        reverse("application-list"), {"offer_id": offer.id, "cv_id": cv.id}, format="json"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_historical_application_reference_remains_after_cv_deletion() -> None:
    user, profile = candidate()
    cv = cv_for(user, profile, 1, PDF_V1)
    application = application_for(profile, cv, organization("9"))

    assert client_for(user).delete(reverse("cv-detail", args=(cv.id,))).status_code == 204

    application.refresh_from_db()
    cv.refresh_from_db()
    assert application.cv_id == cv.id
    assert cv.deleted_at is not None
    assert application.status_history.count() == 1


@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_deleted_cv_remains_available_to_open_application(download_object) -> None:
    user, profile = candidate()
    cv = cv_for(user, profile, 1, PDF_V1)
    application = application_for(profile, cv, organization("10"))
    client = client_for(user)
    client.delete(reverse("cv-detail", args=(cv.id,)))
    download_object.return_value = PDF_V1

    assert client.get(reverse("document-download", args=(cv.document_id,))).status_code == 404
    assert streamed(client.get(reverse("application-cv", args=(application.id,)))) == PDF_V1
    download_object.assert_called_once_with(cv.document.storage_uri)


@patch("backend.apps.candidates.services.records.object_storage.delete_object")
@patch("backend.apps.documents.services.documents.object_storage.download_object")
def test_deleted_cv_purges_only_after_every_application_rejected(
    download_object, delete_object
) -> None:
    from backend.apps.candidates.services.records import purge_cv_bytes

    user, profile = candidate()
    cv = cv_for(user, profile, 1, PDF_V1)
    first = application_for(profile, cv, organization("21"))
    second = application_for(profile, cv, organization("22"))
    client = client_for(user)
    download_object.return_value = PDF_V1
    assert client.delete(reverse("cv-detail", args=(cv.id,))).status_code == 204
    delete_object.assert_not_called()

    first.status = ApplicationStatus.REJECTED
    first.save(update_fields=["status"])
    assert client.get(reverse("application-cv", args=(first.id,))).status_code == 404
    assert streamed(client.get(reverse("application-cv", args=(second.id,)))) == PDF_V1
    assert purge_cv_bytes(cv.id) is False

    second.status = ApplicationStatus.REJECTED
    second.save(update_fields=["status"])
    assert purge_cv_bytes(cv.id) is True
    assert purge_cv_bytes(cv.id) is False
    cv.refresh_from_db()
    assert cv.bytes_purged_at is not None
    delete_object.assert_called_once_with(cv.document.storage_uri)


@patch("backend.apps.candidates.services.records.object_storage.delete_object")
def test_purge_command_retries_storage_failure(delete_object) -> None:
    from django.core.management import call_command

    user, profile = candidate()
    cv = cv_for(user, profile, 1, PDF_V1)
    delete_object.side_effect = RuntimeError("storage unavailable")
    assert client_for(user).delete(reverse("cv-detail", args=(cv.id,))).status_code == 204
    cv.refresh_from_db()
    assert cv.bytes_purged_at is None

    delete_object.side_effect = None
    call_command("purge_deleted_cvs")
    cv.refresh_from_db()
    assert cv.bytes_purged_at is not None
    assert delete_object.call_count == 2


@patch("backend.apps.candidates.services.records.object_storage.delete_object")
def test_final_rejection_purges_deleted_cv_immediately(delete_object) -> None:
    from backend.apps.recruitment.services.application_lifecycle import transition_application

    user, profile = candidate()
    cv = cv_for(user, profile, 1, PDF_V1)
    org = organization("23")
    application = application_for(profile, cv, org)
    reviewer = account("reviewer-final@example.test")
    recruiter(reviewer, org)
    assert client_for(user).delete(reverse("cv-detail", args=(cv.id,))).status_code == 204
    transition_application(reviewer, application.id, ApplicationStatus.REJECTED)

    cv.refresh_from_db()
    assert cv.bytes_purged_at is not None
    delete_object.assert_called_once_with(cv.document.storage_uri)


@pytest.mark.parametrize("status", [ApplicationStatus.WITHDRAWN, ApplicationStatus.HIRED])
@patch("backend.apps.candidates.services.records.object_storage.delete_object")
def test_withdrawn_or_hired_application_retains_deleted_cv(delete_object, status: str) -> None:
    from backend.apps.candidates.services.records import purge_cv_bytes

    user, profile = candidate()
    cv = cv_for(user, profile, 1, PDF_V1)
    application = application_for(profile, cv, organization("24"))
    application.status = status
    application.save(update_fields=["status"])
    assert client_for(user).delete(reverse("cv-detail", args=(cv.id,))).status_code == 204

    assert purge_cv_bytes(cv.id) is False
    assert (
        client_for(user).get(reverse("application-cv", args=(application.id,))).status_code == 404
    )
    cv.refresh_from_db()
    assert cv.bytes_purged_at is None
    delete_object.assert_not_called()


@patch("backend.apps.candidates.services.records.object_storage.delete_object")
def test_deleted_cv_without_applications_purges_immediately(delete_object) -> None:
    user, profile = candidate()
    cv = cv_for(user, profile, 1, PDF_V1)
    assert client_for(user).delete(reverse("cv-detail", args=(cv.id,))).status_code == 204
    cv.refresh_from_db()
    assert cv.bytes_purged_at is not None
    delete_object.assert_called_once_with(cv.document.storage_uri)


def test_deleted_account_cannot_authenticate_or_use_normal_apis() -> None:
    user, _ = candidate()
    access = str(AccessToken.for_user(user))

    assert client_for(user).delete(reverse("user-me")).status_code == 204

    user.refresh_from_db()
    assert user.status == UserStatus.DISABLED
    assert user.deleted_at is not None
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get(reverse("candidate-profile-me")).status_code == 401

    csrf_client = APIClient(enforce_csrf_checks=True)
    csrf_client.get(reverse("csrf-cookie"))
    csrf = csrf_client.cookies["csrftoken"].value
    login = csrf_client.post(
        reverse("token-obtain-pair"),
        {"email": user.email, "password": "test-password"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert login.status_code == 401


def test_account_deletion_preserves_historical_records() -> None:
    user, profile = candidate()
    cv = cv_for(user, profile, 1, PDF_V1)
    application = application_for(profile, cv, organization("11"))

    assert client_for(user).delete(reverse("user-me")).status_code == 204

    assert User.objects.filter(
        pk=user.pk, status=UserStatus.DISABLED, deleted_at__isnull=False
    ).exists()
    assert CandidateProfile.objects.filter(pk=profile.pk, user=user).exists()
    assert CV.objects.filter(pk=cv.pk, candidate=profile).exists()
    assert Application.objects.filter(pk=application.pk, candidate=profile, cv=cv).exists()
    assert ApplicationStatusHistory.objects.filter(application=application).exists()
