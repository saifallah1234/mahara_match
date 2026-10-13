from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import StreamingHttpResponse
from rest_framework.test import APIClient

from ai.speech.providers import MockTTS
from backend.apps.assistant.services import mock_interviews as services
from backend.apps.assistant.services.interview_media import (
    store_artifact,
    submit_recording,
    validate_recording,
)
from backend.apps.candidates.services.records import create_cv
from backend.common.exceptions import DomainNotFoundError, DomainValidationError

pytestmark = pytest.mark.django_db


def test_protected_media_exceeds_document_limit(interview, local_media):
    session = services.create_session(
        interview["candidate"], offer_id=interview["offer"].pk, language="fr", key="media"
    )
    content = b"x" * (11 * 1024 * 1024)
    document = store_artifact(
        session, content=content, mime_type="video/mp4", kind="VIDEO", identity="test"
    )
    job = session.jobs.get()
    job.output = document
    job.status = "SUCCEEDED"
    job.save()
    url = f"/api/v1/mock-interviews/{session.pk}/media/{document.pk}/"
    api = APIClient()
    api.force_authenticate(interview["candidate"])
    response = api.get(url)
    assert response.status_code == 200
    assert isinstance(response, StreamingHttpResponse)
    assert b"".join(response.streaming_content) == content
    assert api.get(f"/api/v1/documents/{document.pk}/").status_code == 404
    with pytest.raises(DomainNotFoundError):
        create_cv(interview["candidate"], {"document": document, "title": "invalid CV"})
    api.force_authenticate(interview["other_candidate"])
    assert api.get(url).status_code == 404
    api.force_authenticate(interview["candidate"])
    assert api.get(f"/api/v1/mock-interviews/{session.pk}/media/{uuid4()}/").status_code == 404


def test_decoded_recording_and_upload_replay(interview, local_media):
    from backend.apps.assistant.services.interview_jobs import run_one

    session = services.create_session(
        interview["candidate"], offer_id=interview["offer"].pk, language="fr", key="record"
    )
    for _ in range(20):
        if not run_one():
            break
    session = services.start_session(interview["candidate"], session.pk)
    assert session.current_turn_id is not None
    audio = MockTTS().synthesize("test", "fr", "test").content
    assert validate_recording(audio).startswith(b"RIFF")

    def upload():
        return SimpleUploadedFile("answer.wav", audio, content_type="audio/wav")

    result = submit_recording(
        interview["candidate"],
        session.pk,
        session.current_turn_id,
        key="answer",
        version=session.version,
        recording=upload(),
    )
    replay = submit_recording(
        interview["candidate"],
        session.pk,
        session.current_turn_id,
        key="answer",
        version=session.version,
        recording=upload(),
    )
    assert result.version == replay.version
    assert result.jobs.filter(stage="ANSWER").count() == 1
    with pytest.raises(DomainValidationError):
        validate_recording(b"not audio")
    with pytest.raises(DomainValidationError):
        validate_recording(
            b"#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXTINF:1,\nhttp://127.0.0.1/private.wav\n"
        )


def test_recording_limits_silence_and_decoder_configuration(settings):
    import wave
    from io import BytesIO

    from backend.apps.assistant.services.interview_contracts import InterviewUnavailable

    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setparams((1, 2, 16000, 16000, "NONE", "not compressed"))
        audio.writeframes(b"\x00" * 32000)
    with pytest.raises(DomainValidationError):
        validate_recording(output.getvalue())
    settings.MOCK_INTERVIEW_MAX_RECORDING_BYTES = 10
    with pytest.raises(DomainValidationError):
        validate_recording(b"x" * 11)
    settings.MOCK_INTERVIEW_MAX_RECORDING_BYTES = 1024 * 1024
    settings.INTERVIEW_FFMPEG = "/missing/interview-ffmpeg"
    with pytest.raises(InterviewUnavailable):
        validate_recording(output.getvalue())


def test_muted_derivatives_preserve_originals(tmp_path, settings):
    import hashlib
    import subprocess

    from django.core.management import call_command

    from backend.apps.assistant.services.interview_contracts import AVATARS
    from backend.apps.assistant.services.interview_media import avatar_path

    # One short source per key keeps this check independent of production media quality.
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "seed.mp4"
    subprocess.run(
        [
            settings.INTERVIEW_FFMPEG,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=64x64:d=0.2",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=0.2",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(source),
        ],
        check=True,
    )
    for filename in AVATARS.values():
        path = sources / filename
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(source.read_bytes())
    settings.MOCK_INTERVIEW_AVATAR_DIR = str(sources)
    settings.MOCK_INTERVIEW_DERIVATIVE_DIR = str(tmp_path / "derivatives")
    before = {key: hashlib.sha256(avatar_path(key).read_bytes()).hexdigest() for key in AVATARS}
    call_command("prepare_interview_avatars")
    for key in AVATARS:
        assert hashlib.sha256(avatar_path(key).read_bytes()).hexdigest() == before[key]
        result = subprocess.run(
            [
                settings.INTERVIEW_FFMPEG,
                "-v",
                "error",
                "-i",
                str(avatar_path(key, derivative=True)),
                "-map",
                "0:a:0",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
        )
        assert result.returncode != 0 and b"matches no streams" in result.stderr


def test_ordinary_document_limits_and_reserved_media_type(interview, settings):
    from backend.apps.documents.services.documents import upload_document

    actor = interview["candidate"]
    with pytest.raises(DomainValidationError):
        upload_document(
            actor,
            SimpleUploadedFile("a.pdf", b"%PDF-test", content_type="application/pdf"),
            "INTERVIEW_TTS",
        )
    settings.DOCUMENT_MAX_UPLOAD_BYTES = 10
    with pytest.raises(DomainValidationError):
        upload_document(
            actor,
            SimpleUploadedFile("a.pdf", b"%PDF-" + b"x" * 10, content_type="application/pdf"),
            "CV",
        )
    with pytest.raises(DomainValidationError):
        upload_document(actor, SimpleUploadedFile("a.wav", b"RIFF", content_type="audio/wav"), "CV")
