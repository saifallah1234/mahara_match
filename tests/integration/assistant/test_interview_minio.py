"""Opt-in check against an explicitly local MinIO; creates only a temporary bucket."""

import os
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from minio.error import S3Error

from ai.speech.providers import MockTTS
from backend.apps.assistant.services import interview_jobs as jobs
from backend.apps.assistant.services import mock_interviews as services
from backend.apps.assistant.services.interview_media import read_artifact, store_artifact
from backend.common.storage import object_storage

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        os.getenv("INTERVIEW_TEST_MINIO") != "1",
        reason="Set INTERVIEW_TEST_MINIO=1 for isolated local MinIO checks.",
    ),
]


@pytest.fixture
def real_minio(settings):
    settings.DEBUG = True
    settings.MOCK_INTERVIEW_BACKEND = "mock"
    settings.TTS_PROVIDER = settings.STT_PROVIDER = "mock"
    settings.MINIO_BUCKET = f"test-interview-{uuid4()}"
    endpoint = settings.MINIO_ENDPOINT
    assert urlsplit(endpoint if "://" in endpoint else f"http://{endpoint}").hostname in {
        "localhost",
        "127.0.0.1",
    }, "This check must use local MinIO."
    storage, bucket = object_storage._configuration()
    storage.make_bucket(bucket)
    try:
        yield storage, bucket
    finally:
        for artifact in storage.list_objects(bucket, recursive=True):
            storage.remove_object(bucket, artifact.object_name)
        storage.remove_bucket(bucket)


def test_complete_flow_with_local_minio(interview, settings, real_minio):
    storage, bucket = real_minio
    session = services.create_session(
        interview["candidate"], offer_id=interview["offer"].pk, language="fr", key="minio"
    )
    for _ in range(20):
        if not jobs.run_one():
            break
    session = services.start_session(interview["candidate"], session.pk)
    for position in (1, 2, 3):
        turn = session.current_turn
        assert turn.position == position
        assert read_artifact(turn.audio).startswith(b"RIFF")
        document = store_artifact(
            session,
            content=MockTTS().synthesize("answer", "fr", "test").content,
            mime_type="audio/wav",
            kind="RECORDING",
            identity=f"recording/{turn.pk}",
        )
        session = services.accept_answer(
            interview["candidate"],
            session.pk,
            turn.pk,
            version=session.version,
            key=str(turn.pk),
            recording=document,
        )
        for _ in range(20):
            if not jobs.run_one():
                break
        session.refresh_from_db()
        with pytest.raises(S3Error) as missing:
            storage.stat_object(bucket, document.storage_uri)
        assert missing.value.code == "NoSuchKey"
    assert session.status == "COMPLETED"
    assert len(session.feedback["questions"]) == 3


def test_worker_queue_flow_with_local_minio(interview, settings, real_minio):
    from tests.integration.assistant.test_interview_queue import run_queue_flow

    run_queue_flow(interview, settings)
