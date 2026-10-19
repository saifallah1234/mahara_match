from importlib import import_module
from io import BytesIO
from pathlib import Path

from ai.speech.providers import Transcript


class FasterWhisperSTT:
    def __init__(self, model_path: str):
        self.path = Path(model_path).expanduser().resolve()
        required = ("model.bin", "config.json", "tokenizer.json")
        if (
            not model_path
            or not self.path.is_dir()
            or any(not (self.path / name).is_file() for name in required)
        ):
            raise ValueError("Configure a complete existing faster-whisper model directory.")
        try:
            self.model = import_module("faster_whisper").WhisperModel(
                str(self.path), device="cpu", compute_type="int8", local_files_only=True
            )
        except ImportError as exc:
            raise ValueError("Install the optional local-speech dependencies.") from exc

    def transcribe(self, audio: bytes, language: str) -> Transcript:
        if language != "fr" or not audio:
            raise ValueError("French audio is required.")
        segments, info = self.model.transcribe(
            BytesIO(audio), language="fr", vad_filter=True, condition_on_previous_text=False
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise ValueError("No speech was detected. Record the answer again.")
        return Transcript(
            text,
            {
                "provider": "faster-whisper",
                "model": self.path.name,
                "language": info.language,
                "simulated": False,
            },
        )
