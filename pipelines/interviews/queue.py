"""Versioned transport contracts; no business records or inference arguments."""

import hashlib
import json
import re
from collections import deque
from typing import Any
from uuid import UUID, uuid4

AVATARS = {
    "base_15": "avatars/avatar_base_15sec.mp4",
    "base_5": "avatars/avatar_base.mp4",
    "thinking_higgs": "avatars/thinking_higs.mp4",
    "thinking_base": "avatars/thinking_avatar.mp4",
    "listening_10": "avatars/listening_higs.mp4",
    "listening_15": "avatars/litsen_nodding_15.mp4",
    "followup": "avatars/followup.mp4",
}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def identity(value: dict[str, Any]) -> None:
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("Unsupported schema.")
    UUID(value["job_id"])
    if type(value.get("generation")) is not int or value["generation"] < 1:
        raise ValueError("Invalid generation.")
    if not re.fullmatch(r"[0-9a-f]{64}", value.get("input_fingerprint", "")):
        raise ValueError("Invalid fingerprint.")


def validate_request(value: dict[str, Any]) -> dict[str, Any]:
    identity(value)
    if set(value) != {
        "schema_version",
        "job_id",
        "generation",
        "input_fingerprint",
        "avatar_key",
        "audio",
    }:
        raise ValueError("Unexpected request fields.")
    if value["avatar_key"] not in AVATARS:
        raise ValueError("Unknown avatar.")
    audio = value["audio"]
    if not isinstance(audio, dict) or set(audio) != {"object_key", "sha256", "duration_ms"}:
        raise ValueError("Invalid audio reference.")
    parts = audio["object_key"].split("/")
    if len(parts) != 4 or parts[:2] != ["interviews", "tts"]:
        raise ValueError("Only private TTS input is permitted.")
    UUID(parts[2])
    UUID(parts[3])
    if not re.fullmatch(r"[0-9a-f]{64}", audio["sha256"]):
        raise ValueError("Invalid audio checksum.")
    if type(audio["duration_ms"]) is not int or not 100 <= audio["duration_ms"] <= 180000:
        raise ValueError("Invalid audio duration.")
    return value


def prefix(value: dict[str, Any]) -> str:
    identity(value)
    return f"interviews/worker/{UUID(value['job_id'])}/{value['generation']}"


def validate_event(value: dict[str, Any]) -> dict[str, Any]:
    identity(value)
    if set(value) != {
        "schema_version",
        "event_id",
        "job_id",
        "generation",
        "input_fingerprint",
        "execution_id",
        "attempt",
        "state",
        "output",
        "simulated",
    }:
        raise ValueError("Unexpected event fields.")
    UUID(value["event_id"])
    UUID(value["execution_id"])
    if type(value["attempt"]) is not int or not 1 <= value["attempt"] <= 3:
        raise ValueError("Invalid attempt.")
    if (
        value["state"] not in {"RUNNING", "SUCCEEDED", "FAILED"}
        or type(value["simulated"]) is not bool
    ):
        raise ValueError("Invalid state.")
    if value["state"] == "SUCCEEDED":
        output = value["output"]
        if not isinstance(output, dict) or set(output) != {
            "object_key",
            "sha256",
            "size_bytes",
            "duration_ms",
        }:
            raise ValueError("Invalid output.")
        if output["object_key"] != prefix(value) + "/output.mp4":
            raise ValueError("Invalid output prefix.")
        if not re.fullmatch(r"[0-9a-f]{64}", output["sha256"]):
            raise ValueError("Invalid output checksum.")
        if (
            type(output["size_bytes"]) is not int
            or not 1 <= output["size_bytes"] <= 100 * 1024 * 1024
        ):
            raise ValueError("Invalid output size.")
        if type(output["duration_ms"]) is not int or not 100 <= output["duration_ms"] <= 181000:
            raise ValueError("Invalid output duration.")
    elif value["output"] is not None:
        raise ValueError("Unexpected output.")
    return value


class SQSQueue:
    def __init__(self, client: Any, url: str):
        self.client, self.url = client, url

    def send(self, value: dict) -> None:
        self.client.send_message(QueueUrl=self.url, MessageBody=json.dumps(value))

    def receive(self, wait: int = 0, visibility: int = 900) -> dict | None:
        result = self.client.receive_message(
            QueueUrl=self.url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=wait,
            VisibilityTimeout=visibility,
        )
        return next(iter(result.get("Messages", [])), None)

    def acknowledge(self, message: dict) -> None:
        self.client.delete_message(QueueUrl=self.url, ReceiptHandle=message["ReceiptHandle"])

    def extend(self, message: dict, seconds: int) -> None:
        self.client.change_message_visibility(
            QueueUrl=self.url, ReceiptHandle=message["ReceiptHandle"], VisibilityTimeout=seconds
        )


class FakeQueue:
    """Explicit test double with retained requests until acknowledgement."""

    def __init__(self):
        self.messages: Any = deque()
        self.deleted: list[str] = []
        self.extensions: list[int] = []

    def send(self, value: dict) -> None:
        self.messages.append({"Body": json.dumps(value), "ReceiptHandle": str(uuid4())})

    def receive(self, wait: int = 0, visibility: int = 900) -> dict | None:
        return self.messages[0] if self.messages else None

    def acknowledge(self, message: dict) -> None:
        self.messages.remove(message)
        self.deleted.append(message["ReceiptHandle"])

    def extend(self, message: dict, seconds: int) -> None:
        self.extensions.append(seconds)
