import ast
import json
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from pipelines.interviews import worker as module
from pipelines.interviews.latentsync import resolve_avatar, run_checked
from pipelines.interviews.queue import FakeQueue, digest, prefix, validate_request
from pipelines.interviews.worker import InterviewWorker, VisibilityLease, worker_lock


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.reads = []

    def read(self, key, limit):
        self.reads.append(key)
        content = self.objects[key]
        if len(content) > limit:
            raise ValueError("limit")
        return content

    def write(self, key, content, mime):
        self.objects[key] = content

    def manifest(self, key):
        return json.loads(self.objects[key]) if key in self.objects else None


@pytest.fixture
def setup_worker(tmp_path, monkeypatch):
    root = tmp_path / "avatars"
    (root / "avatars").mkdir(parents=True)
    (root / "avatars/avatar_base.mp4").write_bytes(b"local-avatar")
    audio_key = f"interviews/tts/{uuid4()}/{uuid4()}"
    request = {
        "schema_version": 1,
        "job_id": str(uuid4()),
        "generation": 1,
        "input_fingerprint": digest(b"inputs"),
        "avatar_key": "base_5",
        "audio": {"object_key": audio_key, "sha256": digest(b"audio"), "duration_ms": 1000},
    }
    storage = MemoryStorage()
    storage.objects[audio_key] = b"audio"
    priority, background, status = FakeQueue(), FakeQueue(), FakeQueue()
    calls = []

    def runner(avatar, audio, duration, scratch, lease_check):
        lease_check()
        calls.append((avatar, audio, scratch))
        return b"generated-video"

    monkeypatch.setattr(module, "validate_video", lambda content, duration, ffmpeg: duration)
    worker = InterviewWorker(
        priority=priority,
        background=background,
        status=status,
        storage=storage,
        avatar_dir=root,
        runner=runner,
        simulated=True,
    )
    return worker, request, storage, calls


def test_duplicate_delivery_reuses_completed_output(setup_worker, caplog):
    worker, request, storage, calls = setup_worker
    worker.priority.send(request)
    worker.priority.send(request)
    with caplog.at_level("INFO", logger="pipelines.interviews.worker"):
        assert worker.run_one() and worker.run_one()
    assert "Received video job=" in caplog.text
    assert "Starting video generation job=" in caplog.text
    assert "Video job succeeded:" in caplog.text
    assert len(calls) == 1 and len(worker.priority.deleted) == 2
    assert not any("avatar" in key for key in storage.reads)
    assert storage.manifest(prefix(request) + "/manifest.json")["attempt"] == 1


@pytest.mark.parametrize("failure", ["status", "ack", "manifest"])
def test_completion_crashes_reuse_result(setup_worker, monkeypatch, failure):
    worker, request, storage, calls = setup_worker
    worker.priority.send(request)
    if failure == "status":
        original = worker.status.send

        def fail(*args):
            value = args[0]
            if value["state"] == "SUCCEEDED":
                raise ConnectionError()
            original(value)

        target, attribute = worker.status, "send"
    elif failure == "ack":
        target, attribute = worker.priority, "acknowledge"
        original = target.acknowledge

        def fail(*args):
            raise ConnectionError()
    else:
        target, attribute = storage, "write"
        original = target.write

        def fail(*args):
            key, content, mime = args
            if key.endswith("manifest.json") and json.loads(content)["state"] == "SUCCEEDED":
                raise ConnectionError()
            original(key, content, mime)

    monkeypatch.setattr(target, attribute, fail)
    worker.run_one()
    assert len(calls) == 1 and not worker.priority.deleted
    monkeypatch.setattr(target, attribute, original)
    worker.run_one()
    assert len(calls) == (2 if failure == "manifest" else 1) and worker.priority.deleted


def test_bounded_retry_survives_redelivery(setup_worker):
    worker, request, storage, calls = setup_worker
    attempts = []

    def fail(*args):
        attempts.append(1)
        raise TimeoutError()

    worker.runner = fail
    worker.priority.send(request)
    for _ in range(5):
        worker.run_one()
    assert len(attempts) == 3 and not worker.priority.deleted
    manifest = storage.manifest(prefix(request) + "/manifest.json")
    assert manifest["attempt"] == 3 and manifest["state"] == "FAILED"
    assert json.loads(worker.status.messages[-1]["Body"])["state"] == "FAILED"


@pytest.mark.parametrize("failure", ["manifest", "avatar", "inference"])
def test_worker_logs_failure_and_retains_request(setup_worker, monkeypatch, caplog, failure):
    worker, request, storage, calls = setup_worker
    if failure == "manifest":

        def fail(*args):
            raise ConnectionError("storage unreachable")

        monkeypatch.setattr(storage, "manifest", fail)
    elif failure == "avatar":
        (worker.avatar_dir / "avatars/avatar_base.mp4").unlink()
    else:

        def fail(*args):
            raise ValueError("inference rejected")

        worker.runner = fail
    worker.priority.send(request)
    assert worker.run_one()
    assert not worker.priority.deleted
    assert request["job_id"] in caplog.text or "worker failure" in caplog.text
    assert any(record.exc_info for record in caplog.records)
    assert not calls


def test_subprocess_failure_reports_bounded_output(tmp_path):
    with pytest.raises(ValueError, match="inference failed") as exc:
        run_checked(
            [
                sys.executable,
                "-c",
                "import sys; print('x' * 5000 + 'inference failed'); sys.exit(1)",
            ],
            cwd=tmp_path,
            timeout=5,
            lease_check=lambda: None,
        )
    assert len(str(exc.value).removeprefix("Media subprocess failed: ")) <= 4000


def test_audio_checksum_and_priority(setup_worker):
    worker, request, storage, calls = setup_worker
    worker.background.send(request)
    worker.priority.send(request | {"job_id": str(uuid4())})
    worker.run_one()
    assert worker.priority.deleted and not worker.background.deleted
    storage.objects[request["audio"]["object_key"]] = b"corrupt"
    worker.run_one()
    assert len(calls) == 1 and not worker.background.deleted


@pytest.mark.parametrize(
    "change",
    [
        {"avatar_key": "../../private"},
        {"video_path": "/private"},
        {"schema_version": 2},
        {"generation": True},
        {"input_fingerprint": "wrong"},
        {
            "audio": {
                "object_key": "https://example.org/private",
                "sha256": digest(b"a"),
                "duration_ms": 1000,
            }
        },
    ],
)
def test_request_trust_boundary(setup_worker, change):
    worker, request, storage, calls = setup_worker
    with pytest.raises((ValueError, TypeError)):
        validate_request(request | change)


def test_missing_avatar_and_symlink_escape(tmp_path):
    (tmp_path / "avatars").mkdir()
    with pytest.raises(ValueError):
        resolve_avatar(tmp_path, "base_5")
    outside = tmp_path.parent / f"{uuid4()}.mp4"
    outside.write_bytes(b"private")
    (tmp_path / "avatars/avatar_base.mp4").symlink_to(outside)
    with pytest.raises(ValueError):
        resolve_avatar(tmp_path, "base_5")


def test_single_worker_lock(tmp_path):
    with worker_lock(tmp_path / "gpu.lock"), pytest.raises(BlockingIOError):
        with worker_lock(tmp_path / "gpu.lock"):
            raise AssertionError("second worker acquired lock")


def test_missing_ffmpeg_rejected_before_worker_receives_jobs(tmp_path):
    from pipelines.interviews.latentsync import LatentSyncRunner

    with pytest.raises(ValueError, match="INTERVIEW_FFMPEG"):
        LatentSyncRunner(
            checkout=tmp_path,
            conda="conda",
            environment="latentsync",
            config=tmp_path / "config.yaml",
            checkpoint=tmp_path / "checkpoint.pt",
            revision="test",
            fps_verified=True,
            ffmpeg=str(tmp_path / "missing-ffmpeg"),
        )


def test_visibility_loss_and_subprocess_deadline(tmp_path, monkeypatch):
    queue = FakeQueue()
    monkeypatch.setattr(queue, "extend", lambda *args: (_ for _ in ()).throw(ConnectionError()))
    with VisibilityLease(queue, {}, visibility=1, heartbeat=0.01) as lease:
        assert lease.lost.wait(1)
        with pytest.raises(ValueError):
            lease.check()
    with pytest.raises(TimeoutError):
        run_checked(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            cwd=tmp_path,
            timeout=0,
            lease_check=lambda: None,
        )


def test_standalone_worker_syntax_is_python310():
    for path in [*Path("pipelines/interviews").glob("*.py"), Path("ai/speech/audio.py")]:
        ast.parse(path.read_text(), filename=str(path), feature_version=(3, 10))
        assert "from django" not in path.read_text()


def test_latentsync_extends_original_for_full_audio(tmp_path, monkeypatch):
    from pipelines.interviews import latentsync

    runner = latentsync.LatentSyncRunner.__new__(latentsync.LatentSyncRunner)
    runner.checkout = tmp_path
    runner.conda, runner.environment, runner.ffmpeg = "/trusted conda", "latentsync", "ffmpeg"
    runner.config, runner.checkpoint = tmp_path / "config.yaml", tmp_path / "checkpoint.pt"
    runner.inference_timeout = 3600
    calls = []
    monkeypatch.setattr(latentsync, "decode_audio", lambda audio, ffmpeg: (b"wav", 16001))
    monkeypatch.setattr(latentsync, "validate_video", lambda *args: 16001)

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if "--video_out_path" in command:
            Path(command[command.index("--video_out_path") + 1]).write_bytes(b"video")
        return b""

    monkeypatch.setattr(latentsync, "run_checked", run)
    assert runner(tmp_path / "original.mp4", b"audio", 16001, tmp_path, lambda: None) == b"video"
    prepare, inference = calls
    assert float(prepare[0][prepare[0].index("-t") + 1]) > 16.001
    assert "-stream_loop" in prepare[0] and "fps=15" in prepare[0]
    assert inference[0][0] == "/trusted conda" and inference[1]["cwd"] == tmp_path
    assert "--enable_deepcache" in inference[0]


def test_visibility_deadline_blocks_work_even_if_renewal_is_stuck(monkeypatch):
    lease = VisibilityLease(FakeQueue(), {}, visibility=900, heartbeat=60)
    monkeypatch.setattr(module.time, "monotonic", lambda: lease.expires_at + 1)
    with pytest.raises(ValueError, match="lease lost"):
        lease.check()
    assert lease.lost.is_set()


def test_real_video_validation_rejects_truncated_audio(settings):
    from ai.speech.providers import MockTTS
    from pipelines.interviews.latentsync import validate_video
    from pipelines.interviews.mock import mock_video

    audio = MockTTS().synthesize("Bonjour", "fr", "test").content
    avatar = resolve_avatar(Path(settings.MOCK_INTERVIEW_AVATAR_DIR), "base_5")
    content = mock_video(avatar, audio, 1000, settings.INTERVIEW_FFMPEG)
    assert abs(validate_video(content, 1000, settings.INTERVIEW_FFMPEG) - 1000) < 100
    with pytest.raises(ValueError, match="duration"):
        validate_video(content, 2000, settings.INTERVIEW_FFMPEG)
