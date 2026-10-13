import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai.speech.audio import decode_audio
from ai.speech.providers import AudioArtifact


class ElevenLabsTTS:
    def __init__(self, api_key: str, *, enabled: bool, ffmpeg: str):
        if not enabled or not api_key:
            raise ValueError(
                "ElevenLabs requires an API key and explicit paid-provider enablement."
            )
        self.api_key = api_key
        self.ffmpeg = ffmpeg

    def synthesize(self, text: str, language: str, voice: str) -> AudioArtifact:
        if language != "fr" or not text.strip() or len(text) > 4000:
            raise ValueError("Use bounded French text.")
        if not re.fullmatch(r"[A-Za-z0-9]{10,64}", voice):
            raise ValueError("Configure an ElevenLabs voice ID.")
        request = Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
            data=json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode(),
            headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                content = response.read(10 * 1024 * 1024 + 1)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise ValueError("ElevenLabs speech request failed.") from exc
        if not content or len(content) > 10 * 1024 * 1024:
            raise ValueError("Speech response is empty or too large.")
        decoded, duration = decode_audio(content, self.ffmpeg)
        return AudioArtifact(
            decoded,
            duration,
            {
                "provider": "elevenlabs",
                "model": "eleven_multilingual_v2",
                "voice": voice,
                "language": language,
                "simulated": False,
            },
        )
