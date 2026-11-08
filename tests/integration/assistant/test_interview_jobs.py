from datetime import timedelta

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from ai.speech.providers import MockTTS, Transcript
from backend.apps.assistant.models import MockInterviewJob
from backend.apps.assistant.services import interview_jobs as jobs
from backend.apps.assistant.services import mock_interviews as services
from backend.apps.assistant.services.interview_media import store_artifact

pytestmark = pytest.mark.django_db


def prepare(data):
    session = services.create_session(
        data["candidate"], offer_id=data["offer"].pk, language="fr", key="create"
    )
    drain()
    session.refresh_from_db()
    return session


def drain():
    for _ in range(30):
        if not jobs.run_one():
            return
    raise AssertionError("Tasks did not settle.")


def test_prepare_failure_is_logged_and_retained_for_retry(interview, monkeypatch, caplog):
    session = services.create_session(
        interview["candidate"], offer_id=interview["offer"].pk, language="fr", key="failure-log"
    )

    def fail(job):
        raise ConnectionError("Ollama is unreachable")

    monkeypatch.setattr(jobs, "compute_job", fail)
    assert jobs.run_one()
    job = session.jobs.get(stage="PREPARE")
    assert job.status == "RETRY_WAIT" and job.error_code == "stage_failed"
    assert f"stage=PREPARE job={job.pk}" in caplog.text
    assert "ConnectionError: Ollama is unreachable" in caplog.text


@pytest.mark.parametrize("followup_after", [None, 1, 2, 3])
def test_complete_local_flow(interview, local_media, monkeypatch, followup_after):
    session = prepare(interview)
    assert session.status == "READY"
    assert session.turns.filter(kind="MAIN").count() == 3
    assert session.evidence["missing_evidence"]
    assert session.jobs.filter(simulated=True).count() > 0
    session = services.start_session(interview["candidate"], session.pk)
    seen = []
    while session.status == "IN_PROGRESS":
        turn = session.current_turn
        seen.append((turn.kind, turn.position))
        text = (
            "à préciser"
            if turn.position == followup_after or turn.kind == "FOLLOWUP"
            else "Voici mon exemple concret."
        )
        monkeypatch.setattr(
            jobs,
            "speech_provider",
            lambda kind, text=text: (
                type(
                    "STT",
                    (),
                    {
                        "transcribe": lambda self, audio, language: Transcript(
                            text, {"provider": "mock", "simulated": True}
                        )
                    },
                )()
                if kind == "stt"
                else MockTTS()
            ),
        )
        recording = store_artifact(
            session,
            content=MockTTS().synthesize("answer", "fr", "test").content,
            mime_type="audio/wav",
            kind="RECORDING",
            identity=f"answer/{turn.pk}",
        )
        session = services.accept_answer(
            interview["candidate"],
            session.pk,
            turn.pk,
            version=session.version,
            key=str(turn.pk),
            recording=recording,
        )
        drain()
        session.refresh_from_db()
    assert session.status == "COMPLETED"
    assert sum(kind == "MAIN" for kind, _ in seen) == 3
    assert sum(kind == "FOLLOWUP" for kind, _ in seen) == (0 if followup_after is None else 1)
    assert len(session.feedback["questions"]) == len(seen)
    assert session.checkpoint["completed_step"] == "FEEDBACK"
    assert all(turn.recording_id is None for turn in session.turns.all())


def test_background_failures_and_missing_initial_media(interview, local_media, monkeypatch):
    original = jobs.mock_video
    monkeypatch.setattr(
        jobs,
        "mock_video",
        lambda avatar, *args: (
            (_ for _ in ()).throw(ValueError())
            if avatar.name in {"litsen_nodding_15.mp4", "listening_higs.mp4"}
            else original(avatar, *args)
        ),
    )
    session = prepare(interview)
    assert session.status == "READY"
    assert session.turns.get(position=2).video_id is None
    assert session.turns.get(position=2).audio_id
    initial = session.jobs.get(stage="VIDEO_REQUIRED", avatar_key="base_15")
    local_media.pop(initial.output.storage_uri)
    from backend.apps.assistant.services.interview_contracts import InterviewUnavailable

    with pytest.raises(InterviewUnavailable):
        services.start_session(interview["candidate"], session.pk)


def test_lease_restart_and_stale_commit(interview, local_media):
    session = services.create_session(
        interview["candidate"], offer_id=interview["offer"].pk, language="fr", key="lease"
    )
    first = jobs.claim_job()
    assert first is not None
    MockInterviewJob.objects.filter(pk=first.pk).update(
        lease_until=timezone.now() - timedelta(seconds=1)
    )
    second = jobs.claim_job()
    assert second is not None
    result = jobs.compute_job(second)
    assert jobs.commit_job(first, result) is False
    assert jobs.commit_job(second, result) is True
    assert session.turns.count() == 3


def test_cleanup_retries_storage_outage(interview, local_media, monkeypatch):
    session = prepare(interview)
    turn = session.turns.get(position=1)
    turn.recording = store_artifact(
        session, content=b"recording", mime_type="audio/wav", kind="RECORDING", identity="cleanup"
    )
    turn.deletion_pending = True
    turn.save()
    from backend.common.storage import object_storage

    delete = object_storage.delete_object
    monkeypatch.setattr(
        object_storage, "delete_object", lambda key: (_ for _ in ()).throw(OSError())
    )
    jobs.cleanup_recordings()
    turn.refresh_from_db()
    assert turn.recording_id and turn.deletion_pending
    monkeypatch.setattr(object_storage, "delete_object", delete)
    jobs.cleanup_recordings()
    turn.refresh_from_db()
    assert not turn.recording_id


def test_failed_stt_retry_and_expiry_reuses_current_turn(interview, local_media, monkeypatch):
    session = services.start_session(interview["candidate"], prepare(interview).pk)
    turn = session.current_turn
    audio = MockTTS().synthesize("answer", "fr", "test").content
    recording = store_artifact(
        session, content=audio, mime_type="audio/wav", kind="RECORDING", identity="stt-retry"
    )
    session = services.accept_answer(
        interview["candidate"],
        session.pk,
        turn.pk,
        version=session.version,
        key="stt",
        recording=recording,
    )
    provider = jobs.speech_provider
    monkeypatch.setattr(
        jobs, "speech_provider", lambda kind: (_ for _ in ()).throw(ValueError("unavailable"))
    )
    for _ in range(3):
        jobs.run_one()
        session.jobs.filter(stage="ANSWER").update(retry_at=timezone.now() - timedelta(seconds=1))
    session.refresh_from_db()
    assert session.status == "FAILED"
    assert session.current_turn_id == turn.pk
    original = session.jobs.get(stage="ANSWER")
    session = services.retry_session(interview["candidate"], session.pk)
    monkeypatch.setattr(jobs, "speech_provider", provider)
    drain()
    original.refresh_from_db()
    assert original.generation == 2 and original.status == "SUCCEEDED"
    assert session.turns.filter(answer_message__isnull=False).count() == 1


def test_followup_speech_retry_reuses_reserved_turn(interview, local_media, monkeypatch):
    session = services.start_session(interview["candidate"], prepare(interview).pk)
    turn = session.current_turn
    recording = store_artifact(
        session,
        content=MockTTS().synthesize("answer", "fr", "test").content,
        mime_type="audio/wav",
        kind="RECORDING",
        identity="followup",
    )
    session = services.accept_answer(
        interview["candidate"],
        session.pk,
        turn.pk,
        version=session.version,
        key="followup",
        recording=recording,
    )
    provider = jobs.speech_provider
    monkeypatch.setattr(
        jobs,
        "speech_provider",
        lambda kind: (
            type(
                "STT",
                (),
                {
                    "transcribe": lambda self, audio, language: Transcript(
                        "à préciser", {"simulated": True}
                    )
                },
            )()
            if kind == "stt"
            else (_ for _ in ()).throw(ValueError())
        ),
    )
    for _ in range(5):
        jobs.run_one()
        session.jobs.filter(stage="FOLLOWUP").update(retry_at=timezone.now() - timedelta(seconds=1))
    session.refresh_from_db()
    assert session.status == "FAILED"
    followup = session.turns.get(kind="FOLLOWUP")
    session = services.retry_session(interview["candidate"], session.pk)
    monkeypatch.setattr(jobs, "speech_provider", provider)
    drain()
    session.refresh_from_db()
    assert session.status == "IN_PROGRESS" and session.current_turn_id == followup.pk
    assert session.turns.filter(kind="FOLLOWUP").count() == 1


def test_feedback_failure_retry_keeps_all_answers(interview, local_media, monkeypatch):
    session = services.start_session(interview["candidate"], prepare(interview).pk)
    compute = jobs.compute_job

    def fail_feedback(job):
        if job.stage == "FEEDBACK":
            raise ValueError("invalid feedback")
        return compute(job)

    monkeypatch.setattr(jobs, "compute_job", fail_feedback)
    for position in (1, 2, 3):
        turn = session.current_turn
        recording = store_artifact(
            session,
            content=MockTTS().synthesize("answer", "fr", "test").content,
            mime_type="audio/wav",
            kind="RECORDING",
            identity=f"feedback/{position}",
        )
        session = services.accept_answer(
            interview["candidate"],
            session.pk,
            turn.pk,
            version=session.version,
            key=f"feedback-{position}",
            recording=recording,
        )
        drain()
        session.refresh_from_db()
    for _ in range(3):
        session.jobs.filter(stage="FEEDBACK").update(retry_at=timezone.now() - timedelta(seconds=1))
        jobs.run_one()
    session.refresh_from_db()
    assert session.status == "FAILED" and not session.feedback
    answers = list(session.turns.values_list("answer_message_id", flat=True))
    monkeypatch.setattr(jobs, "compute_job", compute)
    services.retry_session(interview["candidate"], session.pk)
    drain()
    session.refresh_from_db()
    assert session.status == "COMPLETED"
    assert answers == list(session.turns.values_list("answer_message_id", flat=True))


def test_tts_restart_after_upload_skips_provider(interview, local_media, monkeypatch):
    services.create_session(
        interview["candidate"], offer_id=interview["offer"].pk, language="fr", key="tts-crash"
    )
    prepare_job = jobs.claim_job()
    assert prepare_job is not None
    jobs.commit_job(prepare_job, jobs.compute_job(prepare_job))
    first = jobs.claim_job()
    assert first is not None and first.stage == "TTS"
    output = jobs.compute_job(first)
    type(first).objects.filter(pk=first.pk).update(
        lease_until=timezone.now() - timedelta(seconds=1)
    )
    resumed = jobs.claim_job()
    assert resumed is not None and resumed.pk == first.pk
    monkeypatch.setattr(
        jobs,
        "speech_provider",
        lambda kind: (_ for _ in ()).throw(AssertionError("provider repeated")),
    )
    result = jobs.compute_job(resumed)
    assert result["document"].pk == output["document"].pk
    assert jobs.commit_job(resumed, result)


def test_task_runner_refuses_to_start_when_speech_provider_cannot_be_built(
    interview, local_media, settings
):
    settings.STT_PROVIDER = "faster-whisper"
    settings.FASTER_WHISPER_MODEL_PATH = ""
    session = services.create_session(
        interview["candidate"], offer_id=interview["offer"].pk, language="fr", key="startup"
    )
    before = list(session.jobs.values_list("status", "attempts"))
    with pytest.raises(CommandError, match="faster-whisper.*model directory"):
        call_command("run_interview_tasks", "--once")
    assert list(session.jobs.values_list("status", "attempts")) == before


def test_task_runner_starts_and_processes_jobs_with_mock_backend(interview, local_media):
    session = services.create_session(
        interview["candidate"], offer_id=interview["offer"].pk, language="fr", key="startup-mock"
    )
    call_command("run_interview_tasks", "--once")
    assert session.jobs.get(stage="PREPARE").status == "SUCCEEDED"
