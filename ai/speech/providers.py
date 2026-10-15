import math
import struct
import wave
from dataclasses import dataclass
from io import BytesIO
from typing import Any


@dataclass(frozen=True)
class AudioArtifact:
    content: bytes
    duration_ms: int
    metadata: dict[str, Any]
    mime_type: str = "audio/wav"


@dataclass(frozen=True)
class Transcript:
    text: str
    metadata: dict[str, Any]


class MockTTS:
    def synthesize(self, text: str, language: str, voice: str) -> AudioArtifact:
        if language != "fr":
            raise ValueError("Disabled language.")
        frames = 16000
        output = BytesIO()
        with wave.open(output, "wb") as audio:
            audio.setparams((1, 2, 16000, frames, "NONE", "not compressed"))
            audio.writeframes(
                b"".join(
                    struct.pack("<h", int(1000 * math.sin(i * 2 * math.pi * 220 / 16000)))
                    for i in range(frames)
                )
            )
        return AudioArtifact(
            output.getvalue(),
            1000,
            {"provider": "mock", "model": "tone-v1", "voice": voice, "simulated": True},
        )


class MockSTT:
    def transcribe(self, audio: bytes, language: str) -> Transcript:
        if not audio or language != "fr":
            raise ValueError("Invalid mock transcription input.")
        return Transcript(
            "Je présente un exemple concret de mon expérience professionnelle.",
            {"provider": "mock", "model": "fixed-transcript-v1", "simulated": True},
        )


def tts_provider(name: str, *, allow_mock: bool = False, **configuration: Any) -> Any:
    if name == "mock" and allow_mock:
        return MockTTS()
    if name == "piper":
        from ai.speech.piper import PiperTTS

        return PiperTTS(configuration.get("piper_model", ""))
    if name == "elevenlabs":
        from ai.speech.elevenlabs import ElevenLabsTTS

        return ElevenLabsTTS(
            configuration.get("elevenlabs_key", ""),
            enabled=configuration.get("paid_enabled", False),
            ffmpeg=configuration.get("ffmpeg", "ffmpeg"),
        )
    raise ValueError("TTS provider is disabled or unconfigured.")


def stt_provider(name: str, *, allow_mock: bool = False, **configuration: Any) -> Any:
    if name == "mock" and allow_mock:
        return MockSTT()
    if name == "faster-whisper":
        from ai.speech.faster_whisper import FasterWhisperSTT

        return FasterWhisperSTT(configuration.get("whisper_model", ""))
    raise ValueError("STT provider is disabled or unconfigured.")
