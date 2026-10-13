"""Database-backed application task runner; computation stays outside row locks."""

import logging
import threading
from contextlib import contextmanager
from datetime import timedelta
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone

from ai.llm.prompts.mock_interview import CLOSING_FR
from ai.speech.audio import decode_audio
from ai.speech.providers import stt_provider, tts_provider
from ai.workflows.mock_interview import GRAPH_VERSION, MockInterviewModel, build_interview_graph
from backend.apps.assistant.models import MockInterviewJob, MockInterviewSession, MockInterviewTurn
from backend.apps.assistant.services.interview_contracts import InterviewUnavailable, fingerprint
from backend.apps.assistant.services.interview_evidence import interview_evidence
from backend.apps.assistant.services.interview_media import (
    artifact_id,
    avatar_path,
    check_readiness,
    read_artifact,
    store_artifact,
)
from backend.apps.assistant.services.mock_interviews import (
    request_job,
    reserve_followup,
    transition,
)
from backend.apps.assistant.services.records import (
    record_execution,
    record_message,
    record_tool_call,
)
from backend.apps.documents.models import Document
from backend.common.storage import object_storage
from pipelines.interviews.mock import mock_video

CPU_STAGES = ("PREPARE", "TTS", "ANSWER", "ROUTE", "FOLLOWUP", "FEEDBACK")
logger = logging.getLogger(__name__)


def model_provider() -> Any:
    if settings.MOCK_INTERVIEW_BACKEND == "mock" and settings.DEBUG:
        return MockInterviewModel()
    if settings.MOCK_INTERVIEW_BACKEND == "local":
        from ai.llm.providers.interview import OllamaInterviewModel

        return OllamaInterviewModel()
    raise InterviewUnavailable("Interview reasoning is unconfigured.")


def speech_provider(kind: str) -> Any:
    allow_mock = settings.MOCK_INTERVIEW_BACKEND == "mock" and settings.DEBUG
    factory = tts_provider if kind == "tts" else stt_provider
    try:
        return factory(
            settings.TTS_PROVIDER if kind == "tts" else settings.STT_PROVIDER,
            allow_mock=allow_mock,
            piper_model=settings.PIPER_MODEL_PATH,
            whisper_model=settings.FASTER_WHISPER_MODEL_PATH,
            elevenlabs_key=settings.ELEVENLABS_API_KEY,
            paid_enabled=settings.INTERVIEW_PAID_TTS_ENABLED,
            ffmpeg=settings.INTERVIEW_FFMPEG,
        )
    except ValueError as exc:
        raise InterviewUnavailable(str(exc)) from exc


@transaction.atomic
def claim_job() -> MockInterviewJob | None:
    now = timezone.now()
    stages = CPU_STAGES + (
        ("VIDEO_REQUIRED", "VIDEO_BACKGROUND") if settings.MOCK_INTERVIEW_BACKEND == "mock" else ()
    )
    eligible = (
        Q(status__in=("PENDING", "QUEUED"))
        | Q(status="RETRY_WAIT", retry_at__lte=now)
        | Q(status="RUNNING", lease_until__lt=now)
    )
    job = (
        MockInterviewJob.objects.select_for_update(skip_locked=True, of=("self",))
        .filter(eligible, stage__in=stages)
        .exclude(session__status__in=("CANCELLED", "COMPLETED", "FAILED"))
        .first()
    )
    if job is None:
        return None
    job.attempts += 1
    job.status = "RUNNING"
    job.lease_token = uuid4()
    job.lease_until = now + timedelta(minutes=10)
    job.heartbeat_at = now
    job.save()
    return job


def answer_state(session: MockInterviewSession) -> dict[str, Any]:
    answers = [
        {
            "turn_id": str(turn.pk),
            "kind": turn.kind,
            "text": turn.answer_message.content,
            "question": turn.question_message.content,
        }
        for turn in session.turns.select_related("answer_message", "question_message").filter(
            answer_message__isnull=False
        )
    ]
    return {
        "answers": answers,
        "current_kind": session.current_turn.kind,
        "followup_used": session.turns.filter(kind="FOLLOWUP").exists(),
    }


def compute_job(job: MockInterviewJob) -> dict[str, Any]:
    session = job.session
    simulated = settings.MOCK_INTERVIEW_BACKEND == "mock"
    if simulated and not settings.DEBUG:
        raise InterviewUnavailable("Mock processing is forbidden outside development.")
    if job.stage == "PREPARE":
        graph = build_interview_graph(model_provider(), lambda: interview_evidence(session))
        return graph.invoke({"operation": "prepare"})
    if job.stage in {"TTS", "FOLLOWUP"}:
        identity = f"{job.pk}/{job.generation}/tts"
        existing = Document.objects.filter(pk=artifact_id(session, identity)).first()
        if existing and job.payload.get("speech_metadata"):
            _, duration = decode_audio(read_artifact(existing), settings.INTERVIEW_FFMPEG)
            if existing.scan_status == "UPLOAD_PENDING":
                existing.scan_status = "VALIDATED"
                existing.save(update_fields=["scan_status", "updated_at"])
            return {
                "document": existing,
                "duration_ms": duration,
                "metadata": job.payload["speech_metadata"],
            }
        text = job.payload["text"]
        artifact = speech_provider("tts").synthesize(
            text, session.language, settings.INTERVIEW_VOICE
        )
        content, duration = decode_audio(artifact.content, settings.INTERVIEW_FFMPEG)
        # Persist provider identity before upload; a post-upload crash must reuse its bytes.
        changed = MockInterviewJob.objects.filter(
            pk=job.pk, generation=job.generation, lease_token=job.lease_token, status="RUNNING"
        ).update(payload=job.payload | {"speech_metadata": artifact.metadata})
        if not changed:
            raise InterviewUnavailable("Speech job lease changed.")
        document = store_artifact(
            session,
            content=content,
            mime_type="audio/wav",
            kind="TTS",
            identity=identity,
        )
        return {
            "document": document,
            "duration_ms": duration,
            "metadata": artifact.metadata,
        }
    if job.stage in {"VIDEO_REQUIRED", "VIDEO_BACKGROUND"}:
        if not simulated:
            raise InterviewUnavailable("Video jobs require queue coordination.")
        audio = read_artifact(job.audio)
        content = mock_video(
            avatar_path(job.avatar_key),
            audio,
            job.payload["duration_ms"],
            settings.INTERVIEW_FFMPEG,
        )
        document = store_artifact(
            session,
            content=content,
            mime_type="video/mp4",
            kind="VIDEO",
            identity=f"{job.pk}/{job.generation}/video",
        )
        return {"document": document, "simulated": True}
    if job.stage == "ANSWER":
        turn = job.turn
        if turn.answer_message_id:
            return {"text": turn.answer_message.content, "metadata": turn.provider_metadata}
        audio, _ = decode_audio(
            read_artifact(turn.recording, settings.MOCK_INTERVIEW_MAX_RECORDING_BYTES),
            settings.INTERVIEW_FFMPEG,
        )
        transcript = speech_provider("stt").transcribe(audio, session.language)
        if not transcript.text.strip() or len(transcript.text) > 20000:
            raise ValueError("Empty or oversized transcript.")
        return {"text": transcript.text, "metadata": transcript.metadata}
    if job.stage == "ROUTE":
        return build_interview_graph(model_provider()).invoke(
            {"operation": "answer", **answer_state(session)}
        )
    if job.stage == "FEEDBACK":
        return build_interview_graph(model_provider()).invoke(
            {"operation": "feedback", **answer_state(session)}
        )
    raise ValueError("Unknown interview stage.")


def video_intent(session: MockInterviewSession, tts: MockInterviewJob) -> None:
    role = tts.payload["role"]
    if role == "closing" or tts.turn and tts.turn.kind == "FOLLOWUP":
        return
    required = role in {"intro", "q1"}
    avatar = {"intro": "base_15", "q1": "base_5", "q2": "listening_15", "q3": "listening_10"}[role]
    # Background publication is allowed once both initial intents exist, not after inference.
    if not required and session.jobs.filter(stage="VIDEO_REQUIRED").count() < 2:
        return
    video = request_job(
        session,
        "VIDEO_REQUIRED" if required else "VIDEO_BACKGROUND",
        turn=tts.turn,
        payload={
            "tts_job": str(tts.pk),
            "duration_ms": tts.payload["duration_ms"],
            "avatar": avatar,
            "audio_sha256": tts.output.checksum,
            "provider": tts.payload["provider"],
            "inference_revision": settings.INTERVIEW_INFERENCE_REVISION,
        },
        priority=0 if required else 10,
    )
    if video.avatar_key:
        return
    video.avatar_key = avatar
    video.configuration_fingerprint = fingerprint(
        {
            "revision": settings.INTERVIEW_INFERENCE_REVISION,
            "fps": 15,
            "steps": 8,
            "guidance": 1.5,
            "deepcache": True,
        }
    )
    video.audio = tts.output
    video.status = "QUEUED"
    video.simulated = tts.simulated
    video.save()


@transaction.atomic
def commit_job(job: MockInterviewJob, result: dict[str, Any]) -> bool:
    session = MockInterviewSession.objects.select_for_update().get(pk=job.session_id)
    current = MockInterviewJob.objects.select_for_update().get(pk=job.pk)
    if (
        current.status != "RUNNING"
        or current.generation != job.generation
        or current.lease_token != job.lease_token
        or current.lease_until <= timezone.now()
        or session.status in {"CANCELLED", "COMPLETED", "FAILED"}
    ):
        document = result.get("document")
        if document and session.status == "CANCELLED":
            document.scan_status = "DELETE_PENDING"
            document.save(update_fields=["scan_status", "updated_at"])
        return False
    current.simulated = settings.MOCK_INTERVIEW_BACKEND == "mock"
    if job.stage == "PREPARE":
        session.evidence = result["evidence"]
        session.save(update_fields=["evidence", "updated_at"])
        request = record_message(
            session.conversation,
            sender_type="USER",
            content="Préparer mon entretien blanc.",
            intent="mock_interview",
        )
        execution = record_execution(
            request, route="mock_interview.prepare", status="SUCCEEDED", agent_version=GRAPH_VERSION
        )
        record_tool_call(
            execution,
            {
                "tool_name": "interview_evidence",
                "input_json": {"session_id": str(session.pk)},
                "output_summary_json": {"missing_evidence": result["evidence"]["missing_evidence"]},
                "status": "SUCCEEDED",
            },
        )
        for position, question in enumerate(result["questions"], start=1):
            turn, created = MockInterviewTurn.objects.get_or_create(
                session=session, kind="MAIN", position=position
            )
            if created or not turn.question_message_id:
                turn.question_message = record_message(
                    session.conversation,
                    sender_type="ASSISTANT",
                    content=question,
                    intent="mock_interview_question",
                )
                turn.save()
            request_job(
                session,
                "TTS",
                turn=turn,
                payload={"role": f"q{position}", "text": question},
                priority=0 if position == 1 else 5,
            )
        request_job(
            session, "TTS", payload={"role": "intro", "text": result["introduction"]}, priority=0
        )
        request_job(session, "TTS", payload={"role": "closing", "text": CLOSING_FR}, priority=5)
    elif job.stage in {"TTS", "FOLLOWUP"}:
        current.output = result["document"]
        current.payload = current.payload | {
            "duration_ms": result["duration_ms"],
            "provider": result["metadata"],
        }
        current.save()
        if job.turn_id:
            turn = MockInterviewTurn.objects.get(pk=job.turn_id)
            turn.audio = current.output
            turn.provider_metadata = result["metadata"]
            turn.save()
        if job.stage == "FOLLOWUP":
            session.current_turn = job.turn
            session.save(update_fields=["current_turn", "updated_at"])
            transition(session, "IN_PROGRESS")
        else:
            video_intent(session, current)
    elif job.stage in {"VIDEO_REQUIRED", "VIDEO_BACKGROUND"}:
        current.output = result["document"]
        if job.turn_id:
            turn = MockInterviewTurn.objects.get(pk=job.turn_id)
            turn.video = current.output
            turn.save()
    elif job.stage == "ANSWER":
        assert job.turn_id is not None
        turn = MockInterviewTurn.objects.get(pk=job.turn_id)
        if not turn.answer_message_id:
            turn.answer_message = record_message(
                session.conversation,
                sender_type="USER",
                content=result["text"],
                intent="mock_interview_answer",
            )
        turn.transcription_status = "SUCCEEDED"
        turn.provider_metadata = turn.provider_metadata | {"transcription": result["metadata"]}
        turn.deletion_pending = True
        turn.save()
        request_job(
            session, "ROUTE", turn=turn, payload={"answer": str(turn.answer_message_id)}, priority=0
        )
    elif job.stage == "ROUTE":
        assert job.turn_id is not None
        action = result["next_action"]
        if action == "followup":
            followup = reserve_followup(session.pk, job.turn_id)
            if not followup.question_message_id:
                followup.question_message = record_message(
                    session.conversation,
                    sender_type="ASSISTANT",
                    content=result["followup"],
                    intent="mock_interview_followup",
                )
                followup.save()
            request_job(
                session, "FOLLOWUP", turn=followup, payload={"text": result["followup"]}, priority=0
            )
        else:
            next_turn = (
                session.turns.filter(kind="MAIN", answer_key="").order_by("position").first()
            )
            if next_turn:
                session.current_turn = next_turn
                session.save(update_fields=["current_turn", "updated_at"])
                transition(session, "IN_PROGRESS")
            else:
                if session.turns.filter(kind="FOLLOWUP", answer_message__isnull=True).exists():
                    raise ValueError("Pending follow-up must be answered.")
                transition(session, "EVALUATING")
                request_job(session, "FEEDBACK", priority=0)
    elif job.stage == "FEEDBACK":
        session.feedback = result["feedback"]
        session.save(update_fields=["feedback", "updated_at"])
        for row in result["feedback"]["questions"]:
            session.turns.filter(pk=row["turn_id"]).update(evaluation=row)
        request = session.current_turn.answer_message
        response = record_message(
            session.conversation,
            sender_type="ASSISTANT",
            content=result["feedback"]["summary"],
            intent="mock_interview_feedback",
        )
        record_execution(
            request,
            response_message=response,
            route="mock_interview.feedback",
            status="SUCCEEDED",
            agent_version=GRAPH_VERSION,
        )
        transition(session, "COMPLETED")
    current.status = "SUCCEEDED"
    current.error_code = ""
    current.lease_token = None
    current.lease_until = None
    current.save()
    # Checkpoint contains only serializable business state, never worker objects.
    session.checkpoint = {
        "graph_version": GRAPH_VERSION,
        "completed_step": job.stage,
        "turn_id": str(job.turn_id) if job.turn_id else None,
        "input_fingerprint": job.input_fingerprint,
        "generation": job.generation,
        "state": {"status": session.status, "version": session.version},
    }
    session.save(update_fields=["checkpoint", "updated_at"])
    for tts in session.jobs.filter(stage="TTS", status="SUCCEEDED", payload__role__in=("q2", "q3")):
        video_intent(session, tts)
    return True


@transaction.atomic
def fail_job(job: MockInterviewJob) -> None:
    session = MockInterviewSession.objects.select_for_update().get(pk=job.session_id)
    current = MockInterviewJob.objects.select_for_update().get(pk=job.pk)
    if (
        current.lease_token != job.lease_token
        or current.generation != job.generation
        or session.status in {"CANCELLED", "COMPLETED"}
    ):
        return
    terminal = current.attempts >= settings.MOCK_INTERVIEW_MAX_ATTEMPTS
    current.status = "FAILED" if terminal else "RETRY_WAIT"
    current.retry_at = timezone.now() + timedelta(seconds=min(60, 2**current.attempts))
    current.error_code = "stage_failed"
    current.lease_token = None
    current.lease_until = None
    current.save()
    if job.stage == "ANSWER":
        job.turn.transcription_status = "FAILED"
        job.turn.save()
    if terminal and job.stage != "VIDEO_BACKGROUND":
        session.error_code = "stage_failed"
        session.save(update_fields=["error_code", "updated_at"])
        transition(session, "FAILED")


def promote_ready() -> None:
    # Storage accessibility checks run without holding a session lock.
    for session in MockInterviewSession.objects.filter(status="PREPARING"):
        if check_readiness(session):
            with transaction.atomic():
                current = MockInterviewSession.objects.select_for_update().get(pk=session.pk)
                if current.status == "PREPARING":
                    transition(current, "READY")


def cleanup_recordings() -> None:
    now = timezone.now()
    turns = MockInterviewTurn.objects.filter(recording__isnull=False).filter(
        Q(deletion_pending=True) | Q(recording_expires_at__lte=now)
    )
    for turn in turns:
        document = turn.recording
        turn.deletion_pending = True
        turn.save(update_fields=["deletion_pending", "updated_at"])
        try:
            object_storage.delete_object(document.storage_uri)
        except Exception:
            continue
        with transaction.atomic():
            session = MockInterviewSession.objects.select_for_update().get(pk=turn.session_id)
            current = MockInterviewTurn.objects.select_for_update().get(pk=turn.pk)
            if current.recording_id != document.pk:
                continue
            current.recording = None
            current.deletion_pending = False
            if current.transcription_status != "SUCCEEDED":
                current.answer_key = ""
                current.answer_fingerprint = ""
                current.transcription_status = "PENDING"
                current.jobs.filter(stage="ANSWER").update(status="CANCELLED")
                if session.status in {"THINKING", "FAILED"}:
                    session.status = "IN_PROGRESS"
                    session.version += 1
                    session.save()
            current.save()
            document.scan_status = "PURGED"
            document.save(update_fields=["scan_status", "updated_at"])
    # Crash between upload and answer acceptance leaves unreferenced raw media.
    cutoff = now - timedelta(hours=settings.MOCK_INTERVIEW_RECORDING_RETENTION_HOURS)
    Document.objects.filter(
        type__startswith="INTERVIEW_", scan_status="UPLOAD_PENDING", created_at__lt=cutoff
    ).update(scan_status="DELETE_PENDING")
    Document.objects.filter(
        type="INTERVIEW_RECORDING", created_at__lt=cutoff, interview_recordings__isnull=True
    ).exclude(scan_status="PURGED").update(scan_status="DELETE_PENDING")
    for document in Document.objects.filter(
        type__startswith="INTERVIEW_", scan_status="DELETE_PENDING"
    ):
        try:
            object_storage.delete_object(document.storage_uri)
        except Exception:
            continue
        document.scan_status = "PURGED"
        document.save(update_fields=["scan_status", "updated_at"])


@contextmanager
def cpu_lease(job: MockInterviewJob):
    stopped, lost = threading.Event(), threading.Event()

    def renew():
        try:
            while not stopped.wait(60):
                close_old_connections()
                now = timezone.now()
                changed = (
                    MockInterviewJob.objects.filter(
                        pk=job.pk,
                        generation=job.generation,
                        lease_token=job.lease_token,
                        status="RUNNING",
                        lease_until__gt=now,
                    )
                    .exclude(session__status__in=("FAILED", "CANCELLED", "COMPLETED"))
                    .update(heartbeat_at=now, lease_until=now + timedelta(minutes=10))
                )
                if not changed:
                    lost.set()
                    return
        except Exception:
            lost.set()
        finally:
            close_old_connections()

    thread = threading.Thread(target=renew, daemon=True)
    thread.start()
    try:
        yield lost
    finally:
        stopped.set()
        thread.join(timeout=5)


def run_one() -> bool:
    cleanup_recordings()
    job = claim_job()
    if job is None:
        promote_ready()
        return False
    if job.attempts > settings.MOCK_INTERVIEW_MAX_ATTEMPTS:
        fail_job(job)
        return True
    try:
        with cpu_lease(job) as lost:
            result = compute_job(job)
            if lost.is_set():
                raise InterviewUnavailable("CPU lease lost.")
        commit_job(job, result)
    except Exception:
        logger.exception("Interview job failed: stage=%s job=%s", job.stage, job.pk)
        fail_job(job)
    promote_ready()
    return True
