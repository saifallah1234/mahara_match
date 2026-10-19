"""Private MinIO interview artifacts and owner-scoped playback."""

import hashlib
import struct
import subprocess
import wave
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import FileResponse, StreamingHttpResponse
from django.utils import timezone

from ai.speech.audio import decode_audio
from backend.apps.assistant.models import MockInterviewSession
from backend.apps.assistant.services.interview_contracts import (
    AVATARS,
    InterviewConflict,
    InterviewUnavailable,
)
from backend.apps.assistant.services.mock_interviews import accept_answer, get_session
from backend.apps.documents.models import Document
from backend.apps.documents.services.documents import create_document
from backend.apps.identity.models import User
from backend.common.exceptions import DomainNotFoundError, DomainValidationError
from backend.common.storage import object_storage


def avatar_path(key: str, *, derivative: bool = False) -> Path:
    if key not in AVATARS:
        raise DomainNotFoundError("Avatar not found.")
    root = Path(settings.MOCK_INTERVIEW_AVATAR_DIR).resolve()
    path = (root / AVATARS[key]).resolve()
    if derivative:
        root = Path(settings.MOCK_INTERVIEW_DERIVATIVE_DIR).resolve()
        path = (root / f"{key}.mp4").resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise InterviewUnavailable("Required local avatar is missing.")
    return path


def artifact_id(session: MockInterviewSession, identity: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"interview/{session.pk}/{identity}")


def store_artifact(
    session: MockInterviewSession, *, content: bytes, mime_type: str, kind: str, identity: str
) -> Document:
    document_id = artifact_id(session, identity)
    key = f"interviews/{kind.lower()}/{session.pk}/{document_id}"
    checksum = hashlib.sha256(content).hexdigest()
    document = Document.objects.filter(pk=document_id).first()
    if document and document.checksum != checksum:
        raise InterviewConflict("Artifact identity reused for different bytes.")
    if document and document.scan_status == "VALIDATED":
        return document
    if document is None:
        try:
            with transaction.atomic():
                document = create_document(
                    session.candidate.user,
                    {
                        "id": document_id,
                        "type": f"INTERVIEW_{kind}",
                        "storage_uri": key,
                        "file_name": f"{document_id}.{'mp4' if mime_type == 'video/mp4' else 'wav'}",
                        "mime_type": mime_type,
                        "size_bytes": len(content),
                        "checksum": checksum,
                        "scan_status": "UPLOAD_PENDING",
                        "uploaded_at": timezone.now(),
                    },
                )
        except IntegrityError:
            document = Document.objects.get(pk=document_id)
            if document.checksum != checksum:
                raise InterviewConflict("Artifact identity reused for different bytes.") from None
    try:
        object_storage.upload_object(key, content, mime_type)
    except Exception as exc:
        raise InterviewUnavailable("Interview storage is unavailable.") from exc
    document.scan_status = "VALIDATED"
    document.save(update_fields=["scan_status", "updated_at"])
    return document


def read_artifact(document: Document, limit: int = 100 * 1024 * 1024) -> bytes:
    try:
        content = object_storage.read_bounded(document.storage_uri, limit)
        if (
            len(content) != document.size_bytes
            or hashlib.sha256(content).hexdigest() != document.checksum
        ):
            raise ValueError("Artifact checksum mismatch.")
        return content
    except Exception as exc:
        raise InterviewUnavailable("Interview media is unavailable.") from exc


def validate_recording(content: bytes) -> bytes:
    if not content or len(content) > settings.MOCK_INTERVIEW_MAX_RECORDING_BYTES:
        raise DomainValidationError(
            details={"recording": ["Recording is empty or exceeds 25 MiB."]}
        )
    try:
        decoded, _ = decode_audio(
            content, settings.INTERVIEW_FFMPEG, settings.MOCK_INTERVIEW_MAX_RECORDING_SECONDS
        )
        with wave.open(BytesIO(decoded), "rb") as audio:
            duration = audio.getnframes() / audio.getframerate()
            samples = audio.readframes(audio.getnframes())
        if not 0.1 <= duration <= settings.MOCK_INTERVIEW_MAX_RECORDING_SECONDS:
            raise ValueError("Audio duration exceeds the limit.")
        if not any(abs(sample[0]) > 20 for sample in struct.iter_unpack("<h", samples)):
            raise ValueError("Recording is silent.")
        return decoded
    except FileNotFoundError as exc:
        raise InterviewUnavailable("Audio decoder is unconfigured.") from exc
    except (OSError, subprocess.SubprocessError, wave.Error, ValueError) as exc:
        raise DomainValidationError(
            details={"recording": ["Use decodable, non-silent audio of at most three minutes."]}
        ) from exc


def submit_recording(
    actor: User, session_id: UUID | str, turn_id: UUID | str, *, key: str, version: int, recording
) -> MockInterviewSession:
    session = get_session(actor, session_id)
    turn = session.turns.filter(pk=turn_id).first()
    if turn is None:
        raise DomainNotFoundError("Turn not found.")
    content = bytearray()
    for chunk in recording.chunks():
        content.extend(chunk)
        if len(content) > settings.MOCK_INTERVIEW_MAX_RECORDING_BYTES:
            raise DomainValidationError("Recording exceeds 25 MiB.")
    digest = hashlib.sha256(content).hexdigest()
    if turn.answer_key:
        if turn.answer_key == key and turn.answer_fingerprint == digest:
            return session
        raise InterviewConflict("An answer has already been accepted.")
    if (
        session.version != version
        or session.current_turn_id != turn.pk
        or session.status != "IN_PROGRESS"
    ):
        raise InterviewConflict("Stale version or inactive turn.")
    validate_recording(bytes(content))
    document = store_artifact(
        session,
        content=bytes(content),
        mime_type="audio/webm" if content[:4] == b"\x1aE\xdf\xa3" else "audio/wav",
        kind="RECORDING",
        identity=f"recording/{turn.pk}/{uuid4()}",
    )
    try:
        return accept_answer(
            actor, session_id, turn_id, version=version, key=key, recording=document
        )
    except Exception:
        document.scan_status = "DELETE_PENDING"
        document.save(update_fields=["scan_status", "updated_at"])
        raise


def media_url(session: MockInterviewSession, document: Document | None) -> str | None:
    return f"/mock-interviews/{session.pk}/media/{document.pk}/" if document else None


def playback_descriptors(session: MockInterviewSession) -> dict:
    introduction = session.jobs.filter(
        stage="VIDEO_REQUIRED", avatar_key="base_15", status="SUCCEEDED"
    ).first()
    closing = session.jobs.filter(stage="TTS", payload__role="closing", status="SUCCEEDED").first()
    turn = session.current_turn
    playback: dict[str, Any] = {
        "introduction": media_url(session, introduction.output) if introduction else None,
        "closing_audio": media_url(session, closing.output) if closing else None,
        "neutral_avatar": f"/mock-interviews/{session.pk}/avatars/base_5/",
        "thinking_avatar": f"/mock-interviews/{session.pk}/avatars/thinking_base/",
        "listening_avatar": f"/mock-interviews/{session.pk}/avatars/listening_10/",
        "turn": None,
    }
    if turn:
        playback["turn"] = {
            "id": str(turn.pk),
            "video": media_url(session, turn.video),
            "audio": media_url(session, turn.audio),
            "avatar": f"/mock-interviews/{session.pk}/avatars/{'followup' if turn.kind == 'FOLLOWUP' else 'base_5'}/",
            "simulated": bool(turn.provider_metadata.get("simulated")),
            "lip_synced": False
            if turn.kind == "FOLLOWUP" or turn.provider_metadata.get("simulated")
            else bool(turn.video_id),
        }
    return playback


def check_readiness(session: MockInterviewSession) -> bool:
    turns = list(session.turns.filter(kind="MAIN").order_by("position"))
    required = list(session.jobs.filter(stage="VIDEO_REQUIRED", status="SUCCEEDED"))
    if (
        [turn.position for turn in turns] != [1, 2, 3]
        or any(not turn.question_message_id or not turn.audio_id for turn in turns)
        or {job.avatar_key for job in required} != {"base_15", "base_5"}
    ):
        return False
    closing = session.jobs.filter(stage="TTS", payload__role="closing", status="SUCCEEDED").first()
    if not closing or not closing.output_id:
        return False
    try:
        for key in ("base_5", "followup", "thinking_base", "listening_10"):
            avatar_path(key)
        for document in (
            [job.output for job in required] + [turn.audio for turn in turns] + [closing.output]
        ):
            if (
                document is None
                or object_storage.object_metadata(document.storage_uri)[0] != document.size_bytes
            ):
                return False
        return True
    except Exception:
        return False


def stream_media(
    actor: User, session_id: UUID | str, document_id: UUID | str
) -> StreamingHttpResponse:
    session = get_session(actor, session_id)
    documents = {str(value) for value in session.jobs.values_list("audio_id", flat=True) if value}
    documents.update(
        str(value)
        for value in session.jobs.filter(status="SUCCEEDED").values_list("output_id", flat=True)
        if value
    )
    for audio_id, video_id in session.turns.values_list("audio_id", "video_id"):
        documents.update(str(value) for value in (audio_id, video_id) if value)
    if str(document_id) not in documents:
        raise DomainNotFoundError("Media not found.")
    document = Document.objects.get(pk=document_id, owner_user=actor)
    try:
        size, _ = object_storage.object_metadata(document.storage_uri)
        if size != document.size_bytes:
            raise ValueError("Size mismatch.")
    except Exception as exc:
        raise InterviewUnavailable("Media is unavailable.") from exc
    response = StreamingHttpResponse(
        object_storage.stream_object(document.storage_uri), content_type=document.mime_type
    )
    response["Content-Length"] = str(size)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def stream_avatar(actor: User, session_id: UUID | str, key: str) -> FileResponse:
    get_session(actor, session_id)
    source = avatar_path(key)
    derivative = Path(settings.MOCK_INTERVIEW_DERIVATIVE_DIR) / f"{key}.mp4"
    if derivative.exists():
        source = avatar_path(key, derivative=True)
    response = FileResponse(source.open("rb"), content_type="video/mp4")
    response["Cache-Control"] = "private, no-store"
    return response
