from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest
from django.db import close_old_connections, connection, transaction
from django.urls import reverse
from rest_framework.test import APIClient

from backend.apps.candidates.models import CandidateProfile
from backend.apps.identity.models import User
from backend.apps.training.models import TrainingEnrollment, TrainingSession
from backend.apps.training.services.enrollments import (
    DuplicateEnrollmentError,
    EnrollmentLimitReachedError,
    RegistrationDeadlinePassedError,
    cancel_enrollment,
    enroll_candidate,
    update_progress,
)
from backend.apps.training.services.sessions import delete_session, update_session
from backend.common.exceptions import DomainPermissionError, DomainValidationError

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def enroll(phase3: dict[str, Any], who: str = "candidate") -> TrainingEnrollment:
    return enroll_candidate(phase3[who], {"session_id": phase3["session"].id})


def test_deadline_and_inclusive_boundary(phase3: dict[str, Any]) -> None:
    deadline = phase3["session"].registration_deadline
    with patch("backend.apps.training.services.enrollments.timezone.now", return_value=deadline):
        assert enroll(phase3).status == "REGISTERED"


def test_after_deadline_rejected(phase3: dict[str, Any]) -> None:
    deadline = phase3["session"].registration_deadline
    with patch(
        "backend.apps.training.services.enrollments.timezone.now",
        return_value=deadline + timedelta(seconds=1),
    ):
        with pytest.raises(RegistrationDeadlinePassedError):
            enroll(phase3)
    assert TrainingEnrollment.objects.count() == 0


def test_full_capacity_and_dropping_frees_slot_without_reenrollment(phase3: dict[str, Any]) -> None:
    enrollment = enroll(phase3)
    with pytest.raises(EnrollmentLimitReachedError):
        enroll(phase3, "other_candidate")
    cancel_enrollment(phase3["candidate"], enrollment)
    with pytest.raises(DuplicateEnrollmentError):
        enroll(phase3)
    assert enroll(phase3, "other_candidate").status == "REGISTERED"
    with pytest.raises(DuplicateEnrollmentError):
        enroll(phase3, "other_candidate")


@pytest.mark.parametrize("status", ["REGISTERED", "IN_PROGRESS", "COMPLETED"])
def test_all_non_dropped_states_consume_capacity(phase3: dict[str, Any], status: str) -> None:
    TrainingEnrollment.objects.create(
        session=phase3["session"], candidate=phase3["candidate_profile"], status=status
    )
    with pytest.raises(EnrollmentLimitReachedError):
        enroll(phase3, "other_candidate")


def test_progress_lifecycle_and_stale_drop_cannot_change_completed(phase3: dict[str, Any]) -> None:
    original = enroll(phase3)
    with pytest.raises(DomainValidationError):
        update_progress(phase3["provider"], original, 100)
    progress = update_progress(phase3["provider"], original, 25)
    assert progress.status == "IN_PROGRESS"
    completed = update_progress(phase3["provider"], original, 100)
    assert completed.status == "COMPLETED"
    assert completed.completed_at is not None
    with pytest.raises(DomainValidationError):
        cancel_enrollment(phase3["candidate"], original)
    with pytest.raises(DomainValidationError):
        update_progress(phase3["provider"], original, 50)


@pytest.mark.parametrize("rate", [-1, 101, float("nan"), float("inf"), -float("inf")])
def test_invalid_progress_rejected_at_service_boundary(phase3: dict[str, Any], rate: float) -> None:
    enrollment = enroll(phase3)
    with pytest.raises(DomainValidationError):
        update_progress(phase3["provider"], enrollment, rate)
    enrollment.refresh_from_db()
    assert enrollment.status == "REGISTERED" and enrollment.completion_rate == 0


def test_stale_progress_cannot_revive_dropped_and_repeat_drop_is_idempotent(
    phase3: dict[str, Any],
) -> None:
    original = enroll(phase3)
    dropped = cancel_enrollment(phase3["candidate"], original)
    assert cancel_enrollment(phase3["candidate"], original).updated_at == dropped.updated_at
    with pytest.raises(DomainValidationError):
        update_progress(phase3["provider"], original, 25)


def test_cancellation_preserves_history_and_blocks_enrollment_progress(
    phase3: dict[str, Any],
) -> None:
    session = phase3["session"]
    for status in ("REGISTERED", "IN_PROGRESS", "COMPLETED", "DROPPED"):
        user = User.objects.create_user(
            f"{status}@example.test", first_name="Test", last_name="User", status="ACTIVE"
        )
        TrainingEnrollment.objects.create(
            session=session, candidate=CandidateProfile.objects.create(user=user), status=status
        )
    before = list(TrainingEnrollment.objects.order_by("id").values())
    delete_session(phase3["provider"], session)
    assert list(TrainingEnrollment.objects.order_by("id").values()) == before
    with pytest.raises(DomainValidationError):
        enroll(phase3)
    registered = TrainingEnrollment.objects.get(status="REGISTERED")
    with pytest.raises(DomainValidationError):
        update_progress(phase3["provider"], registered, 25)
    assert cancel_enrollment(phase3["provider"], registered).status == "DROPPED"


@pytest.mark.parametrize("status", ["COMPLETED", "CANCELLED"])
def test_terminal_session_cannot_reopen_through_api(phase3: dict[str, Any], status: str) -> None:
    session = phase3["session"]
    session.status = status
    session.save()
    client = APIClient()
    client.force_authenticate(phase3["provider"])
    response = client.patch(
        reverse("training:session-detail", args=(session.id,)), {"status": "PLANNED"}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    session.refresh_from_db()
    assert session.status == status


def test_capacity_reduction_cannot_overbook_and_stale_session_cannot_reopen(
    phase3: dict[str, Any],
) -> None:
    session = update_session(phase3["provider"], phase3["session"], {"capacity": 2})
    enroll(phase3)
    enroll(phase3, "other_candidate")
    with pytest.raises(DomainValidationError):
        update_session(phase3["provider"], session, {"capacity": 1})
    delete_session(phase3["provider"], session)
    with pytest.raises(DomainValidationError):
        update_session(phase3["provider"], session, {"status": "ONGOING"})


def test_provider_actions_are_scoped_and_candidate_cannot_update_progress(
    phase3: dict[str, Any],
) -> None:
    enrollment = enroll(phase3)
    for actor in (phase3["candidate"], phase3["other_provider"]):
        with pytest.raises(DomainPermissionError):
            update_progress(actor, enrollment, 20)
    with pytest.raises(DomainPermissionError):
        cancel_enrollment(phase3["other_provider"], enrollment)
    with pytest.raises(DomainPermissionError):
        update_session(phase3["other_provider"], phase3["session"], {"capacity": 2})
    with pytest.raises(DomainPermissionError):
        enroll_candidate(
            phase3["other_provider"],
            {
                "session_id": phase3["session"].id,
                "candidate_id": phase3["other_candidate_profile"].id,
            },
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_candidate", [False, True])
def test_concurrent_enrollment_never_overbooks_or_duplicates(
    phase3: dict[str, Any], same_candidate: bool
) -> None:
    if not connection.features.has_select_for_update:
        pytest.skip("Requires isolated PostgreSQL row locks.")
    barrier = Barrier(2)
    session_id = phase3["session"].id
    user_ids = [
        phase3["candidate"].id,
        phase3["candidate" if same_candidate else "other_candidate"].id,
    ]

    def attempt(user_id: UUID) -> str:
        close_old_connections()
        try:
            actor = User.objects.get(pk=user_id)
            barrier.wait(timeout=10)
            try:
                enroll_candidate(actor, {"session_id": session_id})
                return "enrolled"
            except (EnrollmentLimitReachedError, DuplicateEnrollmentError) as exc:
                return exc.code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, user_ids))
    assert results.count("enrolled") == 1
    assert TrainingEnrollment.objects.filter(session_id=session_id).count() == 1
    assert set(results) == {
        "enrolled",
        "training_duplicate_enrollment" if same_candidate else "training_session_full",
    }


@pytest.mark.django_db(transaction=True)
def test_concurrent_drop_and_completion_preserve_terminal_state(phase3: dict[str, Any]) -> None:
    if not connection.features.has_select_for_update:
        pytest.skip("Requires isolated PostgreSQL row locks.")
    original = update_progress(phase3["provider"], enroll(phase3), 25)
    barrier = Barrier(2)

    def attempt(operation: str) -> str:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                if operation == "complete":
                    update_progress(phase3["provider"], original, 100)
                else:
                    cancel_enrollment(phase3["candidate"], original)
                return "changed"
            except DomainValidationError:
                return "terminal"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, ("complete", "drop")))
    assert sorted(results) == ["changed", "terminal"]
    original.refresh_from_db()
    if original.status == "COMPLETED":
        assert original.completion_rate == 100 and original.completed_at is not None
    else:
        assert original.status == "DROPPED"
        assert original.completion_rate == 25 and original.completed_at is None


@pytest.mark.django_db(transaction=True)
def test_progress_waiting_on_cancellation_observes_cancelled_session(
    phase3: dict[str, Any],
) -> None:
    if not connection.features.has_select_for_update:
        pytest.skip("Requires isolated PostgreSQL row locks.")
    enrollment = enroll(phase3)
    started = Event()

    def progress() -> str:
        close_old_connections()
        try:
            started.set()
            try:
                update_progress(phase3["provider"], enrollment, 25)
                return "changed"
            except DomainValidationError:
                return "cancelled"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            session = TrainingSession.objects.select_for_update().get(pk=phase3["session"].pk)
            future = executor.submit(progress)
            assert started.wait(timeout=10)
            delete_session(phase3["provider"], session)
        assert future.result(timeout=10) == "cancelled"
    enrollment.refresh_from_db()
    assert enrollment.status == "REGISTERED" and enrollment.completion_rate == 0
