# Placement: tests/integration/platform/test_notifications.py
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from backend.apps.candidates.models import CV
from backend.apps.documents.models import Document
from backend.apps.identity.models import OnboardingRequest, User
from backend.apps.identity.services.onboarding import reject
from backend.apps.platform.models import Notification
from backend.apps.recruitment.models import Application, JobOffer
from backend.apps.recruitment.services.application_lifecycle import (
    submit_application,
    transition_application,
)
from backend.apps.recruitment.services.interview_lifecycle import (
    finish_interview,
    schedule_interview,
)
from backend.apps.training.models import TrainingEnrollment
from backend.apps.training.services.enrollments import (
    cancel_enrollment,
    enroll_candidate,
    update_progress,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _types(user: User) -> list[str]:
    return sorted(Notification.objects.filter(user=user).values_list("type", flat=True))


@pytest.fixture
def offer(phase3: dict[str, Any]) -> JobOffer:
    return JobOffer.objects.create(
        organization=phase3["recruiter_org"],
        created_by=phase3["recruiter"],
        title="Python developer",
        description="Build tested services",
        easy_apply=True,
        status="PUBLISHED",
    )


@pytest.fixture
def cv(phase3: dict[str, Any]) -> CV:
    document = Document.objects.create(
        owner_user=phase3["candidate"],
        type="CV",
        storage_uri="private/cv",
        file_name="cv.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        uploaded_at=timezone.now(),
    )
    return CV.objects.create(
        candidate=phase3["candidate_profile"], document=document, title="CV", version_number=1
    )


@pytest.fixture
def application(phase3: dict[str, Any], offer: JobOffer, cv: CV) -> Application:
    return Application.objects.create(
        candidate=phase3["candidate_profile"], offer=offer, cv=cv, status="SUBMITTED"
    )


def test_submission_notifies_only_recruiters_of_the_offer_organization(
    phase3: dict[str, Any], offer: JobOffer, cv: CV
) -> None:
    submit_application(
        phase3["candidate"], {"cv_id": str(cv.id), "offer_id": str(offer.id), "cover_letter": ""}
    )

    assert _types(phase3["recruiter"]) == ["recruitment.application.submitted"]
    assert _types(phase3["other_recruiter"]) == []
    assert _types(phase3["candidate"]) == []


def test_status_change_notifies_the_candidate_not_the_recruiter(
    phase3: dict[str, Any], application: Application
) -> None:
    transition_application(phase3["recruiter"], application.id, "UNDER_REVIEW")

    assert _types(phase3["candidate"]) == ["recruitment.application.status_changed"]
    assert _types(phase3["recruiter"]) == []


def test_withdrawal_notifies_recruiters_not_the_candidate(
    phase3: dict[str, Any], application: Application
) -> None:
    transition_application(phase3["candidate"], application.id, "WITHDRAWN")

    assert _types(phase3["recruiter"]) == ["recruitment.application.withdrawn"]
    assert _types(phase3["candidate"]) == []


def test_interview_scheduled_then_cancelled_notifies_the_candidate(
    phase3: dict[str, Any], application: Application
) -> None:
    application.status = "INTERVIEW"
    application.save(update_fields=["status"])
    interview = schedule_interview(
        phase3["recruiter"],
        {
            "application_id": application.id,
            "type": "VIDEO",
            "scheduled_at": timezone.now() + timedelta(days=3),
            "duration_minutes": 45,
            "location_or_url": "https://example.test/room",
        },
    )

    finish_interview(phase3["recruiter"], interview.id, "CANCELLED")

    assert _types(phase3["candidate"]) == [
        "recruitment.interview.cancelled",
        "recruitment.interview.scheduled",
    ]
    assert _types(phase3["recruiter"]) == []


def test_enrollment_and_progress_notify_the_right_people(phase3: dict[str, Any]) -> None:
    enroll_candidate(phase3["candidate"], {"session_id": phase3["session"].id})
    enrollment = TrainingEnrollment.objects.get(candidate=phase3["candidate_profile"])

    assert _types(phase3["provider"]) == ["training.enrollment.created"]
    assert _types(phase3["other_provider"]) == []

    update_progress(phase3["provider"], enrollment, 10.0)

    assert _types(phase3["candidate"]) == ["training.enrollment.status_changed"]
    assert _types(phase3["provider"]) == ["training.enrollment.created"]


def test_candidate_cancellation_notifies_training_managers(phase3: dict[str, Any]) -> None:
    enroll_candidate(phase3["candidate"], {"session_id": phase3["session"].id})
    enrollment = TrainingEnrollment.objects.get(candidate=phase3["candidate_profile"])

    cancel_enrollment(phase3["candidate"], enrollment)

    assert _types(phase3["provider"]) == [
        "training.enrollment.cancelled",
        "training.enrollment.created",
    ]
    assert _types(phase3["candidate"]) == []


def test_onboarding_rejection_notifies_the_requester(phase3: dict[str, Any]) -> None:
    requester = User.objects.create_user(
        "requester@example.test", first_name="Req", last_name="Uester", status="PENDING"
    )
    request = OnboardingRequest.objects.create(
        user=requester,
        requested_role="RECRUITER",
        organization_name="Acme",
        matricule_fiscal="1234567A00000",
    )

    reject(phase3["admin"], request.id)

    assert _types(requester) == ["identity.onboarding.rejected"]
