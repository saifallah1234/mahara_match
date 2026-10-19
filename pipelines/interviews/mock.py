import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def mock_video(avatar: Path, audio: bytes, duration_ms: int, ffmpeg: str) -> bytes:
    """Mux simulated audio over the original motion; this performs no lip-sync."""
    with TemporaryDirectory(prefix="mock-interview-") as scratch:
        directory = Path(scratch)
        (directory / "audio.wav").write_bytes(audio)
        output = directory / "simulated.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-stream_loop",
                "-1",
                "-i",
                str(avatar),
                "-i",
                str(directory / "audio.wav"),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-t",
                str(duration_ms / 1000),
                "-vf",
                "scale=360:-2,fps=15",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return output.read_bytes()
