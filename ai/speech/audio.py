import subprocess
import wave
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory


def decode_audio(content: bytes, ffmpeg: str, max_seconds: int = 180) -> tuple[bytes, int]:
    """Bound decoding and measure the bytes actually produced by the provider."""
    with TemporaryDirectory(prefix="interview-audio-") as scratch:
        source, output = Path(scratch) / "input", Path(scratch) / "audio.wav"
        source.write_bytes(content)
        subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "wav,matroska,webm,ogg,mov,mp4,m4a,3gp,3g2,mj2,mp3",
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-t",
                str(max_seconds + 1),
                str(output),
            ],
            check=True,
            timeout=30,
            capture_output=True,
        )
        decoded = output.read_bytes()
    with wave.open(BytesIO(decoded), "rb") as audio:
        duration = round(audio.getnframes() * 1000 / audio.getframerate())
    if not 100 <= duration <= max_seconds * 1000:
        raise ValueError("Audio duration is outside the allowed range.")
    return decoded, duration
