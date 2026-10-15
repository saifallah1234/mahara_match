from hashlib import sha256
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.assistant.models import MockInterviewJob, MockInterviewTurn
from backend.apps.assistant.services import mock_interviews as services
from backend.apps.assistant.services.interview_contracts import InterviewConflict
from backend.apps.assistant.services.records import record_message
from backend.apps.documents.models import Document

pytestmark = pytest.mark.django_db


def create(data, key="create-1"):
    return services.create_session(
        data["candidate"], offer_id=data["offer"].pk, language="fr", key=key
    )


def client(actor):
    api = APIClient()
    api.force_authenticate(actor)
    return api


def recording(actor, content=b"recorded answer"):
    return Document.objects.create(
        owner_user=actor,
        type="INTERVIEW_RECORDING",
        storage_uri=f"interviews/recordings/{uuid4()}",
        file_name="answer.webm",
        mime_type="audio/webm",
        size_bytes=len(content),
        checksum=sha256(content).hexdigest(),
        scan_status="VALIDATED",
        uploaded_at=timezone.now(),
    )


def active(data):
    session = create(data)
    for position in (1, 2, 3):
        MockInterviewTurn.objects.create(session=session, position=position)
    session.status = "READY"
    session.save()
    with patch(
        "backend.apps.assistant.services.interview_media.check_readiness", return_value=True
    ):
        return services.start_session(data["candidate"], session.pk)


def test_create_is_durable_idempotent_and_private(interview):
    api = client(interview["candidate"])
    payload = {"offer_id": str(interview["offer"].pk), "language": "fr"}
    with patch("backend.common.storage.object_storage.upload_object") as storage:
        first = api.post(
            "/api/v1/mock-interviews/", payload, format="json", HTTP_IDEMPOTENCY_KEY="create"
        )
        again = api.post(
            "/api/v1/mock-interviews/", payload, format="json", HTTP_IDEMPOTENCY_KEY="create"
        )
        storage.assert_not_called()
    assert first.status_code == again.status_code == 202
    assert first.data["id"] == again.data["id"]
    assert MockInterviewJob.objects.count() == 1
    assert MockInterviewJob.objects.get().status == "PENDING"
    url = f"/api/v1/mock-interviews/{first.data['id']}/"
    assert client(interview["other_candidate"]).get(url).status_code == 404
    assert client(interview["recruiter"]).get(url).status_code == 403
    assert client(interview["other_candidate"]).get("/api/v1/mock-interviews/").data["count"] == 0
    assert "input_fingerprint" not in first.data


def test_validation_and_disabled_integrations(interview):
    api = client(interview["candidate"])
    base = {"offer_id": str(interview["offer"].pk)}
    for change, status in (
        ({"language": "en"}, 400),
        ({"offer_id": str(uuid4())}, 404),
        ({"cv_id": str(uuid4())}, 404),
    ):
        response = api.post(
            "/api/v1/mock-interviews/",
            base | change,
            format="json",
            HTTP_IDEMPOTENCY_KEY="validation",
        )
        assert response.status_code == status
    assert api.post("/api/v1/mock-interviews/", base, format="json").status_code == 400
    with override_settings(MOCK_INTERVIEW_ENABLED=False):
        assert (
            api.post(
                "/api/v1/mock-interviews/", base, format="json", HTTP_IDEMPOTENCY_KEY="disabled"
            ).status_code
            == 503
        )
    session = create(interview)
    assert api.post(f"/api/v1/mock-interviews/{session.pk}/start/").status_code == 409


def test_main_and_followup_constraints(interview):
    session = create(interview)
    parent = MockInterviewTurn.objects.create(session=session, position=1)
    for position in (0, 4, None, 1):
        with pytest.raises(IntegrityError), transaction.atomic():
            MockInterviewTurn.objects.create(session=session, position=position)
    MockInterviewTurn.objects.create(session=session, kind="FOLLOWUP", parent=parent)
    with pytest.raises(IntegrityError), transaction.atomic():
        MockInterviewTurn.objects.create(session=session, kind="FOLLOWUP", parent=parent)


def test_answer_idempotency_and_versions(interview):
    session = active(interview)
    actor = interview["candidate"]
    audio = recording(actor)
    kwargs = dict(version=session.version, key="answer-1", recording=audio)
    with pytest.raises(InterviewConflict):
        services.accept_answer(
            actor,
            session.pk,
            session.current_turn_id,
            **(kwargs | {"version": session.version - 1}),
        )
    accepted = services.accept_answer(actor, session.pk, session.current_turn_id, **kwargs)
    replay = services.accept_answer(actor, session.pk, session.current_turn_id, **kwargs)
    assert accepted.version == replay.version
    assert replay.status == "THINKING"
    assert replay.jobs.filter(stage="ANSWER").count() == 1
    with pytest.raises(InterviewConflict):
        services.accept_answer(
            actor,
            session.pk,
            session.current_turn_id,
            **(kwargs | {"recording": recording(actor, b"changed")}),
        )
    with pytest.raises(InterviewConflict):
        services.accept_answer(
            actor, session.pk, session.current_turn_id, **(kwargs | {"key": "second"})
        )


def test_followup_reservation_reuses_turn_and_retry_job(interview):
    session = active(interview)
    actor = interview["candidate"]
    session = services.accept_answer(
        actor,
        session.pk,
        session.current_turn_id,
        version=session.version,
        key="answer",
        recording=recording(actor),
    )
    parent = session.current_turn
    parent.answer_message = record_message(
        session.conversation, sender_type="USER", content="My answer"
    )
    parent.save()
    followup = services.reserve_followup(session.pk, parent.pk)
    assert services.reserve_followup(session.pk, parent.pk).pk == followup.pk
    job = session.jobs.get(stage="ANSWER")
    job.status = "FAILED"
    job.save()
    services.transition(session, "FAILED")
    retried = services.retry_session(actor, session.pk)
    job.refresh_from_db()
    assert job.generation == 2 and job.status == "PENDING"
    assert retried.turns.filter(kind="FOLLOWUP").get().pk == followup.pk


def test_conflicting_create_and_cancel(interview):
    session = create(interview)
    with pytest.raises(InterviewConflict):
        services.create_session(
            interview["candidate"], offer_id=uuid4(), language="fr", key="create-1"
        )
    cancelled = services.cancel_session(interview["candidate"], session.pk)
    assert cancelled.status == "CANCELLED"
    assert cancelled.jobs.get().status == "CANCELLED"
    assert services.cancel_session(interview["candidate"], session.pk).version == cancelled.version
    with pytest.raises(InterviewConflict):
        services.retry_session(interview["candidate"], session.pk)
