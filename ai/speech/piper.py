import json
import wave
from importlib import import_module
from io import BytesIO
from pathlib import Path

from ai.speech.providers import AudioArtifact


class PiperTTS:
    def __init__(self, model_path: str):
        self.path = Path(model_path).expanduser().resolve()
        configuration = Path(str(self.path) + ".json")
        if not model_path or not self.path.is_file() or not configuration.is_file():
            raise ValueError("Configure an existing Piper ONNX model and its JSON file.")
        model = json.loads(configuration.read_text())
        if not model.get("language", {}).get("code", "").startswith("fr"):
            raise ValueError("Configure a French Piper voice.")
        try:
            self.voice = import_module("piper").PiperVoice.load(str(self.path))
        except ImportError as exc:
            raise ValueError("Install the optional local-speech dependencies.") from exc

    def synthesize(self, text: str, language: str, voice: str) -> AudioArtifact:
        if language != "fr" or not text.strip() or not voice:
            raise ValueError("French text and a configured voice are required.")
        output = BytesIO()
        with wave.open(output, "wb") as audio:
            self.voice.synthesize_wav(text, audio)
        content = output.getvalue()
        with wave.open(BytesIO(content), "rb") as audio:
            duration_ms = round(audio.getnframes() * 1000 / audio.getframerate())
        if duration_ms <= 0:
            raise ValueError("Speech provider produced empty audio.")
        return AudioArtifact(
            content,
            duration_ms,
            {
                "provider": "piper",
                "model": self.path.name,
                "voice": self.path.stem,
                "language": language,
                "simulated": False,
            },
        )
