import json
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from django.utils import timezone
from minio.error import S3Error

from backend.apps.assistant.services import interview_jobs as jobs
from backend.apps.assistant.services import interview_queue as coordinator
from backend.apps.assistant.services import mock_interviews as services
from backend.common.storage import object_storage
from pipelines.interviews.mock import mock_video
from pipelines.interviews.queue import FakeQueue, prefix
from pipelines.interviews.worker import InterviewWorker

pytestmark = pytest.mark.django_db


def queued_session(interview):
    session = services.create_session(
        interview["candidate"], offer_id=interview["offer"].pk, language="fr", key="queued"
    )
    # Leave video work to the queue while real task stages retain the same leases.
    for _ in range(6):
        job = jobs.claim_job()
        if job and job.stage.startswith("VIDEO"):
            job.status = "QUEUED"
            job.save()
            # Complete the remaining TTS jobs explicitly, avoiding queued video claims.
            for pending in session.jobs.filter(stage="TTS", status="PENDING"):
                pending.status, pending.lease_token = "RUNNING", uuid4()
                pending.attempts = 1
                pending.lease_until = timezone.now() + timedelta(minutes=10)
                pending.save()
                jobs.commit_job(pending, jobs.compute_job(pending))
            break
        if job:
            jobs.commit_job(job, jobs.compute_job(job))
    return session


class ApplicationStorage:
    def read(self, key, limit):
        return object_storage.read_bounded(key, limit)

    def write(self, key, content, mime):
        object_storage.upload_object(key, content, mime)

    def manifest(self, key):
        try:
            return json.loads(self.read(key, 64 * 1024))
        except KeyError:
            return None
        except S3Error as exc:
            if exc.code != "NoSuchKey":
                raise
            return None


def test_queue_flow_priority_readiness_duplicate_and_stale(interview, local_media, settings):
    run_queue_flow(interview, settings)


def run_queue_flow(interview, settings):
    session = queued_session(interview)
    priority, background, status = FakeQueue(), FakeQueue(), FakeQueue()
    while coordinator.publish_one(priority, background):
        pass
    assert len(priority.messages) == len(background.messages) == 2
    assert not coordinator.publish_one(priority, background)
    worker = InterviewWorker(
        priority=priority,
        background=background,
        status=status,
        storage=ApplicationStorage(),
        avatar_dir=Path(settings.MOCK_INTERVIEW_AVATAR_DIR),
        ffmpeg=settings.INTERVIEW_FFMPEG,
        simulated=True,
        runner=lambda avatar, audio, duration, scratch, check: mock_video(
            avatar, audio, duration, settings.INTERVIEW_FFMPEG
        ),
    )
    assert worker.run_one() and worker.run_one()
    while coordinator.ingest_one(status):
        pass
    session.refresh_from_db()
    assert session.status == "READY" and len(background.messages) == 2
    job = session.jobs.filter(stage="VIDEO_REQUIRED").first()
    request = coordinator.envelope(job)
    manifest = ApplicationStorage().manifest(prefix(request) + "/manifest.json")
    late = worker.event(request, manifest, "RUNNING")
    coordinator.ingest(late)
    coordinator.ingest(late | {"generation": 99})
    job.refresh_from_db()
    assert job.status == "SUCCEEDED" and job.output_id
    # Stopped GPU does not block Q2/Q3 fallback or erase READY.
    services.start_session(interview["candidate"], session.pk)


def test_publication_crash_replays_and_background_waits(interview, local_media, monkeypatch):
    queued_session(interview)
    priority, background = FakeQueue(), FakeQueue()
    first = priority.send

    def sent_then_crashed(value):
        first(value)
        raise ConnectionError()

    monkeypatch.setattr(priority, "send", sent_then_crashed)
    with pytest.raises(ConnectionError):
        coordinator.publish_one(priority, background)
    assert not background.messages
    monkeypatch.setattr(priority, "send", first)
    while coordinator.publish_one(priority, background):
        pass
    assert len(priority.messages) == 3 and len(background.messages) == 2


def test_bad_output_never_acknowledged_and_terminal_manifest_reconciled(interview, local_media):
    session = queued_session(interview)
    priority, background, status = FakeQueue(), FakeQueue(), FakeQueue()
    coordinator.publish_one(priority, background)
    job = session.jobs.filter(publication_status="PUBLISHED").get()
    request = coordinator.envelope(job)
    manifest = {
        "input_fingerprint": job.input_fingerprint,
        "execution_id": str(uuid4()),
        "attempt": 3,
        "state": "FAILED",
        "simulated": True,
    }
    ApplicationStorage().write(
        prefix(request) + "/manifest.json", json.dumps(manifest).encode(), "application/json"
    )
    coordinator.reconcile_manifests()
    session.refresh_from_db()
    assert session.status == "FAILED"
    services.retry_session(interview["candidate"], session.pk)
    job.refresh_from_db()
    assert job.generation == 2 and job.publication_status == "UNPUBLISHED"
    stale = request | {
        "event_id": str(uuid4()),
        "execution_id": manifest["execution_id"],
        "attempt": 3,
        "state": "FAILED",
        "output": None,
        "simulated": True,
    }
    stale.pop("avatar_key")
    stale.pop("audio")
    status.send(stale)
    coordinator.ingest_one(status)
    job.refresh_from_db()
    assert job.status == "PENDING" and status.deleted


def test_live_queue_access_requires_explicit_enablement(settings):
    from backend.apps.assistant.services.interview_contracts import InterviewUnavailable

    settings.MOCK_INTERVIEW_ALLOW_LIVE_AWS = False
    with pytest.raises(InterviewUnavailable):
        coordinator.configured_queues()


def test_stopped_worker_and_corrupt_output(interview, local_media, settings):
    from backend.apps.assistant.api.mock_interview_serializers import SessionReadSerializer
    from pipelines.interviews.queue import digest

    session = queued_session(interview)
    priority, background, status = FakeQueue(), FakeQueue(), FakeQueue()
    coordinator.publish_one(priority, background)
    job = session.jobs.filter(publication_status="PUBLISHED").get()
    job.updated_at = timezone.now() - timedelta(minutes=16)
    job.save(update_fields=["heartbeat_at"])
    type(job).objects.filter(pk=job.pk).update(
        updated_at=timezone.now() - timedelta(minutes=16),
        heartbeat_at=timezone.now() - timedelta(minutes=16),
    )
    assert SessionReadSerializer(session).data["availability"]["worker"] == "stalled"
    assert session.status == "PREPARING"
    event = {
        "schema_version": 1,
        "event_id": str(uuid4()),
        "job_id": str(job.pk),
        "generation": job.generation,
        "input_fingerprint": job.input_fingerprint,
        "execution_id": str(uuid4()),
        "attempt": 1,
        "state": "SUCCEEDED",
        "simulated": True,
        "output": {
            "object_key": prefix(coordinator.envelope(job)) + "/output.mp4",
            "sha256": digest(b"expected"),
            "size_bytes": 7,
            "duration_ms": 1000,
        },
    }
    local_media[event["output"]["object_key"]] = (b"corrupt", "video/mp4")
    status.send(event)
    with pytest.raises(ValueError):
        coordinator.ingest_one(status)
    assert not status.deleted
    settings.DEBUG = False
    with pytest.raises(ValueError, match="Simulated"):
        coordinator.ingest(event)
