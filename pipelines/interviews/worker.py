"""MinIO/SQS worker; has no Django or relational database dependency."""

import fcntl
import json
import logging
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

from pipelines.interviews.latentsync import resolve_avatar, validate_video
from pipelines.interviews.queue import digest, prefix, validate_request

logger = logging.getLogger(__name__)


@contextmanager
def worker_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


class VisibilityLease:
    def __init__(self, queue: Any, message: dict, *, visibility: int = 900, heartbeat: float = 60):
        if not 1 <= visibility <= 43100 or not 0 < heartbeat < visibility:
            raise ValueError("Invalid visibility/heartbeat configuration.")
        self.queue, self.message = queue, message
        self.visibility, self.heartbeat = visibility, heartbeat
        self.started = time.monotonic()
        self.expires_at = self.started + visibility
        self.lost = threading.Event()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.renew, daemon=True)
        self.on_heartbeat: Any = None

    def renew(self):
        while not self.stopped.wait(self.heartbeat):
            try:
                self.check()
                remaining = int(43100 - (time.monotonic() - self.started))
                if remaining < self.visibility:
                    raise ValueError("Maximum SQS processing interval reached.")
                sent_at = time.monotonic()
                self.queue.extend(self.message, min(self.visibility, remaining))
                self.expires_at = sent_at + min(self.visibility, remaining)
                if self.on_heartbeat:
                    self.on_heartbeat()
            except Exception:
                self.lost.set()
                return

    def check(self):
        if (
            self.lost.is_set()
            or time.monotonic() >= self.expires_at
            or time.monotonic() - self.started >= 43100
        ):
            self.lost.set()
            raise ValueError("Queue visibility lease lost.")

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stopped.set()
        self.thread.join(timeout=5)


class InterviewWorker:
    def __init__(
        self,
        *,
        priority: Any,
        background: Any,
        status: Any,
        storage: Any,
        avatar_dir: Path,
        runner: Any,
        ffmpeg: str = "ffmpeg",
        simulated: bool = False,
        visibility: int = 900,
        heartbeat: float = 60,
    ):
        self.priority, self.background, self.status, self.storage = (
            priority,
            background,
            status,
            storage,
        )
        self.avatar_dir, self.runner, self.ffmpeg = avatar_dir, runner, ffmpeg
        self.simulated, self.visibility, self.heartbeat = simulated, visibility, heartbeat

    def event(self, request: dict, manifest: dict, state: str) -> dict:
        return {
            "schema_version": 1,
            "event_id": str(uuid4()),
            "job_id": request["job_id"],
            "generation": request["generation"],
            "input_fingerprint": request["input_fingerprint"],
            "execution_id": manifest["execution_id"],
            "attempt": manifest["attempt"],
            "state": state,
            "output": manifest.get("output") if state == "SUCCEEDED" else None,
            "simulated": self.simulated,
        }

    def process(self, queue: Any, message: dict) -> bool:
        request = validate_request(json.loads(message["Body"]))
        logger.info("Received video job=%s generation=%s", request["job_id"], request["generation"])
        manifest_key = prefix(request) + "/manifest.json"
        manifest = self.storage.manifest(manifest_key) or {
            "attempt": 0,
            "input_fingerprint": request["input_fingerprint"],
            "state": "PENDING",
            "simulated": self.simulated,
        }
        if manifest["input_fingerprint"] != request["input_fingerprint"]:
            raise ValueError("Generation fingerprint mismatch.")
        if manifest.get("simulated", False) != self.simulated:
            raise ValueError("Cannot reuse a result from a different worker mode.")
        with VisibilityLease(
            queue, message, visibility=self.visibility, heartbeat=self.heartbeat
        ) as lease:
            if manifest["state"] == "SUCCEEDED":
                output = manifest["output"]
                content = self.storage.read(output["object_key"], 100 * 1024 * 1024)
                if len(content) != output["size_bytes"] or digest(content) != output["sha256"]:
                    raise ValueError("Stored completed result is corrupt.")
                validate_video(content, request["audio"]["duration_ms"], self.ffmpeg)
            else:
                if manifest["attempt"] >= 3:
                    self.status.send(self.event(request, manifest, "FAILED"))
                    return False
                manifest.update(
                    attempt=manifest["attempt"] + 1, execution_id=str(uuid4()), state="RUNNING"
                )
                self.storage.write(manifest_key, json.dumps(manifest).encode(), "application/json")
                lease.on_heartbeat = lambda: self.status.send(
                    self.event(request, manifest, "RUNNING")
                )
                try:
                    self.status.send(self.event(request, manifest, "RUNNING"))
                    avatar = resolve_avatar(self.avatar_dir, request["avatar_key"])
                    audio = self.storage.read(request["audio"]["object_key"], 10 * 1024 * 1024)
                    if digest(audio) != request["audio"]["sha256"]:
                        raise ValueError("Audio checksum mismatch.")
                    lease.check()
                    with TemporaryDirectory(prefix="latentsync-job-") as scratch:
                        logger.info("Starting video generation job=%s", request["job_id"])
                        content = self.runner(
                            avatar,
                            audio,
                            request["audio"]["duration_ms"],
                            Path(scratch),
                            lease.check,
                        )
                    duration = validate_video(content, request["audio"]["duration_ms"], self.ffmpeg)
                    if len(content) > 100 * 1024 * 1024:
                        raise ValueError("Generated video exceeds limit.")
                    lease.check()
                    output = {
                        "object_key": prefix(request) + "/output.mp4",
                        "sha256": digest(content),
                        "size_bytes": len(content),
                        "duration_ms": duration,
                    }
                    self.storage.write(output["object_key"], content, "video/mp4")
                    lease.check()
                    manifest.update(state="SUCCEEDED", output=output)
                    self.storage.write(
                        manifest_key, json.dumps(manifest).encode(), "application/json"
                    )
                except Exception:
                    logger.exception(
                        "Video job failed: job=%s attempt=%s",
                        request["job_id"],
                        manifest["attempt"],
                    )
                    # Never acknowledge failed inference; durable count survives redelivery.
                    manifest["state"] = "FAILED" if manifest["attempt"] >= 3 else "RETRY_WAIT"
                    if not lease.lost.is_set():
                        self.storage.write(
                            manifest_key, json.dumps(manifest).encode(), "application/json"
                        )
                    if manifest["state"] == "FAILED":
                        self.status.send(self.event(request, manifest, "FAILED"))
                    return False
            lease.check()
            self.status.send(self.event(request, manifest, "SUCCEEDED"))
            lease.check()
            queue.acknowledge(message)
            logger.info("Video job succeeded: job=%s", request["job_id"])
            return True

    def run_one(self) -> bool:
        queue = self.priority
        message = queue.receive(visibility=self.visibility)
        if message is None:
            queue = self.background
            # No long background poll: check priority again before starting inference.
            message = queue.receive(visibility=self.visibility)
            priority = self.priority.receive(visibility=self.visibility)
            if priority is not None:
                queue, message = self.priority, priority
        if message is None:
            return False
        try:
            self.process(queue, message)
        except Exception:
            # Malformed messages and storage/status outages are retried/redriven, never deleted.
            logger.exception("Interview request retained after worker failure.")
        return True
