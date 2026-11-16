import wave
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
        # The job passes the 16 kHz mono WAV decoded by FFmpeg. Hand faster-whisper the samples:
        # its own PyAV decoder calls av.open(metadata_errors=...), which PyAV 19 rejects.
        try:
            with wave.open(BytesIO(audio), "rb") as source:
                layout = (source.getnchannels(), source.getsampwidth(), source.getframerate())
                frames = source.readframes(source.getnframes())
        except (wave.Error, EOFError) as exc:
            raise ValueError("Expected 16 kHz mono 16-bit WAV audio.") from exc
        if layout != (1, 2, 16000):
            raise ValueError("Expected 16 kHz mono 16-bit WAV audio.")
        numpy = import_module("numpy")
        samples = numpy.frombuffer(frames, dtype="<i2").astype(numpy.float32) / 32768.0
        segments, info = self.model.transcribe(
            samples, language="fr", vad_filter=True, condition_on_previous_text=False
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
