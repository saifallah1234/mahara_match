"""Durable publication and result ingestion, independent of long CPU tasks."""

import json
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from backend.apps.assistant.models import MockInterviewJob, MockInterviewSession
from backend.apps.assistant.services.interview_contracts import InterviewUnavailable
from backend.apps.assistant.services.interview_jobs import cleanup_recordings, promote_ready
from backend.apps.assistant.services.mock_interviews import transition
from backend.apps.documents.services.documents import create_document
from backend.common.storage import object_storage
from pipelines.interviews.latentsync import validate_video
from pipelines.interviews.queue import SQSQueue, digest, validate_event, validate_request


def configured_queues():
    if not settings.MOCK_INTERVIEW_ALLOW_LIVE_AWS:
        raise InterviewUnavailable("Live AWS queue access is disabled.")
    import boto3  # type: ignore[import-untyped]

    urls = (
        settings.INTERVIEW_PRIORITY_QUEUE_URL,
        settings.INTERVIEW_BACKGROUND_QUEUE_URL,
        settings.INTERVIEW_STATUS_QUEUE_URL,
    )
    if not settings.INTERVIEW_AWS_REGION or not all(urls):
        raise InterviewUnavailable("Configure the three SQS queues and region.")
    client = boto3.client("sqs", region_name=settings.INTERVIEW_AWS_REGION)
    return tuple(SQSQueue(client, url) for url in urls)


def envelope(job: MockInterviewJob) -> dict:
    return validate_request(
        {
            "schema_version": 1,
            "job_id": str(job.pk),
            "generation": job.generation,
            "input_fingerprint": job.input_fingerprint,
            "avatar_key": job.avatar_key,
            "audio": {
                "object_key": job.audio.storage_uri,
                "sha256": job.audio.checksum,
                "duration_ms": job.payload["duration_ms"],
            },
        }
    )


def publish_one(priority, background) -> bool:
    now = timezone.now()
    with transaction.atomic():
        job = (
            MockInterviewJob.objects.select_for_update(skip_locked=True, of=("self",))
            .filter(
                stage__in=("VIDEO_REQUIRED", "VIDEO_BACKGROUND"), status__in=("PENDING", "QUEUED")
            )
            .filter(
                Q(publication_status="UNPUBLISHED")
                | Q(publication_status="SENDING", lease_until__lt=now)
            )
            .exclude(session__status__in=("CANCELLED", "COMPLETED", "FAILED"))
            .first()
        )
        if job is None:
            return False
        if (
            job.stage == "VIDEO_BACKGROUND"
            and job.session.jobs.filter(
                stage="VIDEO_REQUIRED", publication_status="PUBLISHED"
            ).count()
            != 2
        ):
            return False
        request = envelope(job)
        job.publication_status = "SENDING"
        job.lease_token = uuid4()
        job.lease_until = now + timedelta(minutes=2)
        job.save()
    queue = priority if job.stage == "VIDEO_REQUIRED" else background
    try:
        queue.send(request)
    except Exception:
        MockInterviewJob.objects.filter(
            pk=job.pk, generation=job.generation, lease_token=job.lease_token
        ).update(publication_status="UNPUBLISHED", lease_token=None, lease_until=None)
        raise
    # A crash after send yields a duplicate, which the generation manifest absorbs.
    published = MockInterviewJob.objects.filter(
        pk=job.pk, generation=job.generation, lease_token=job.lease_token
    )
    published.filter(status__in=("PENDING", "QUEUED")).update(status="QUEUED", heartbeat_at=None)
    published.update(
        publication_status="PUBLISHED",
        lease_token=None,
        lease_until=None,
        updated_at=timezone.now(),
    )
    return True


def ingest(event: dict) -> None:
    value = validate_event(event)
    job = MockInterviewJob.objects.filter(
        pk=value["job_id"],
        generation=value["generation"],
        input_fingerprint=value["input_fingerprint"],
        stage__in=("VIDEO_REQUIRED", "VIDEO_BACKGROUND"),
    ).first()
    if (
        job is None
        or job.status in {"SUCCEEDED", "CANCELLED", "FAILED"}
        or job.session.status in {"CANCELLED", "COMPLETED", "FAILED"}
    ):
        return
    if value["simulated"] and not (settings.DEBUG and settings.MOCK_INTERVIEW_BACKEND == "mock"):
        raise ValueError("Simulated worker results are forbidden in this configuration.")
    if value["attempt"] < job.attempts:
        return
    output = value["output"]
    if value["state"] == "SUCCEEDED":
        content = object_storage.read_bounded(output["object_key"], 100 * 1024 * 1024)
        if len(content) != output["size_bytes"] or digest(content) != output["sha256"]:
            raise ValueError("Worker output integrity mismatch.")
        duration = validate_video(content, job.payload["duration_ms"], settings.INTERVIEW_FFMPEG)
        if abs(duration - output["duration_ms"]) > 100:
            raise ValueError("Worker duration metadata mismatch.")
    with transaction.atomic():
        session = MockInterviewSession.objects.select_for_update().get(pk=job.session_id)
        current = MockInterviewJob.objects.select_for_update().get(pk=job.pk)
        if (
            current.generation != value["generation"]
            or current.input_fingerprint != value["input_fingerprint"]
            or current.status in {"SUCCEEDED", "FAILED", "CANCELLED"}
            or session.status in {"CANCELLED", "COMPLETED", "FAILED"}
            or value["attempt"] < current.attempts
        ):
            return
        current.attempts = value["attempt"]
        current.heartbeat_at = timezone.now()
        current.status = value["state"]
        current.simulated = value["simulated"]
        current.payload = current.payload | {
            "execution_id": value["execution_id"],
            "last_event_id": value["event_id"],
        }
        if output:
            document_id = uuid5(
                NAMESPACE_URL, f"interview-worker/{current.pk}/{current.generation}"
            )
            document = current.output
            if document is None:
                document = create_document(
                    session.candidate.user,
                    {
                        "id": document_id,
                        "type": "INTERVIEW_VIDEO",
                        "storage_uri": output["object_key"],
                        "file_name": f"{document_id}.mp4",
                        "mime_type": "video/mp4",
                        "size_bytes": output["size_bytes"],
                        "checksum": output["sha256"],
                        "scan_status": "VALIDATED",
                        "uploaded_at": timezone.now(),
                    },
                )
            current.output = document
            if current.turn_id:
                current.turn.video = document
                current.turn.save(update_fields=["video", "updated_at"])
        if value["state"] == "FAILED":
            current.error_code = "worker_attempts_exhausted"
            if current.stage == "VIDEO_REQUIRED":
                session.error_code = current.error_code
                session.save(update_fields=["error_code", "updated_at"])
                transition(session, "FAILED")
        current.save()


def ingest_one(status_queue, *, wait=0) -> bool:
    message = status_queue.receive(wait=wait)
    if message is None:
        return False
    ingest(json.loads(message["Body"]))
    # ingest returns after the transaction commits, including stale/duplicate events.
    status_queue.acknowledge(message)
    promote_ready()
    return True


def reconcile_manifests() -> None:
    """Recover terminal manifests even when status publication/DLQ delivery failed."""
    from pipelines.interviews.queue import prefix

    for job in MockInterviewJob.objects.filter(
        stage__in=("VIDEO_REQUIRED", "VIDEO_BACKGROUND"),
        publication_status="PUBLISHED",
        status__in=("QUEUED", "RUNNING"),
    ):
        key = prefix(envelope(job)) + "/manifest.json"
        try:
            manifest = json.loads(object_storage.read_bounded(key, 64 * 1024))
            if manifest["input_fingerprint"] != job.input_fingerprint or manifest["state"] not in {
                "SUCCEEDED",
                "FAILED",
            }:
                continue
            ingest(
                {
                    "schema_version": 1,
                    "event_id": str(uuid4()),
                    "job_id": str(job.pk),
                    "generation": job.generation,
                    "input_fingerprint": job.input_fingerprint,
                    "execution_id": manifest["execution_id"],
                    "attempt": manifest["attempt"],
                    "state": manifest["state"],
                    "output": manifest.get("output") if manifest["state"] == "SUCCEEDED" else None,
                    "simulated": manifest.get("simulated", False),
                }
            )
        except Exception:
            continue


def coordinate_once(priority, background, status) -> None:
    # Bounded batches keep publication, ingestion and cleanup responsive.
    for _ in range(20):
        if not publish_one(priority, background):
            break
    for _ in range(20):
        if not ingest_one(status):
            break
    reconcile_manifests()
    cleanup_recordings()
    promote_ready()
